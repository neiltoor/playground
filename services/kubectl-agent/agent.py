"""
Agent logic for kubectl operations.
Orchestrates conversation with Claude and kubectl command execution.
"""

import os
import json
import uuid
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

import httpx


ANTHROPIC_SERVICE_URL = os.getenv("ANTHROPIC_SERVICE_URL", "http://anthropic-service:8001")
KUBECTL_SERVICE_URL = os.getenv("KUBECTL_SERVICE_URL", "http://kubectl-service:8003")
MAX_AGENT_ITERATIONS = 10
COMMAND_TIMEOUT = 30

SYSTEM_PROMPT = """You are a Kubernetes assistant with access to kubectl commands. Help users understand and manage their Kubernetes cluster.

When the user asks about their cluster, you can execute kubectl commands to get information.

IMPORTANT: You must respond with valid JSON in one of these formats:

1. To execute kubectl commands:
{"action": "execute", "commands": ["get pods -n default", "get services"]}

2. To provide a final response to the user:
{"action": "respond", "message": "Your helpful response here explaining what you found"}

Rules:
- The commands should NOT include "kubectl" prefix - just the arguments (e.g., "get pods" not "kubectl get pods")
- You can run multiple commands in one request if needed
- After seeing command results, interpret them in plain language for the user
- If a command fails, explain why and suggest alternatives
- Always be helpful and explain what the commands show
- For complex questions, gather information first with commands, then respond

Examples of valid commands:
- "get pods -n default"
- "get pods --all-namespaces"
- "describe pod my-pod -n default"
- "get deployments -o wide"
- "logs my-pod -n default --tail=50"
- "get nodes"
- "top pods -n default"
- "get events -n default --sort-by='.lastTimestamp'"
"""


@dataclass
class ConversationState:
    """Maintains conversation state for a session."""
    conversation_id: str
    messages: List[Dict[str, str]] = field(default_factory=list)
    commands_executed: List[str] = field(default_factory=list)


# In-memory conversation store (could be Redis in production)
conversations: Dict[str, ConversationState] = {}


def get_or_create_conversation(conversation_id: Optional[str] = None) -> ConversationState:
    """Get existing conversation or create a new one."""
    if conversation_id and conversation_id in conversations:
        return conversations[conversation_id]

    new_id = conversation_id or str(uuid.uuid4())
    conv = ConversationState(conversation_id=new_id)
    conversations[new_id] = conv
    return conv


async def call_anthropic(messages: List[Dict[str, str]], system: str) -> str:
    """Call anthropic-service to get Claude's response."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{ANTHROPIC_SERVICE_URL}/chat",
            json={
                "messages": messages,
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.1,
                "max_tokens": 2048,
                "system": system
            }
        )
        response.raise_for_status()
        data = response.json()
        return data.get("content", "")


async def execute_kubectl(command: str) -> Dict[str, Any]:
    """Execute a kubectl command via kubectl-service."""
    async with httpx.AsyncClient(timeout=COMMAND_TIMEOUT + 10) as client:
        response = await client.post(
            f"{KUBECTL_SERVICE_URL}/execute",
            json={
                "command": command,
                "timeout": COMMAND_TIMEOUT
            }
        )
        response.raise_for_status()
        return response.json()


def parse_agent_response(response: str) -> Dict[str, Any]:
    """Parse Claude's JSON response."""
    # Try to extract JSON from the response
    response = response.strip()

    # Handle case where response is wrapped in markdown code blocks
    if "```json" in response:
        match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            response = match.group(1)
    elif "```" in response:
        match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            response = match.group(1)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # If JSON parsing fails, treat it as a direct response
        return {"action": "respond", "message": response}


async def run_agent(user_message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Run the agent loop to process a user message.

    Returns:
        Dict with conversation_id, response, commands_executed
    """
    conv = get_or_create_conversation(conversation_id)

    # Add user message to history
    conv.messages.append({"role": "user", "content": user_message})

    iteration = 0
    commands_this_turn = []

    while iteration < MAX_AGENT_ITERATIONS:
        iteration += 1

        # Call Claude
        try:
            claude_response = await call_anthropic(conv.messages, SYSTEM_PROMPT)
        except httpx.HTTPError as e:
            return {
                "conversation_id": conv.conversation_id,
                "response": f"Error communicating with Claude: {str(e)}",
                "commands_executed": commands_this_turn,
                "error": True
            }

        # Parse the response
        parsed = parse_agent_response(claude_response)
        action = parsed.get("action", "respond")

        if action == "execute":
            commands = parsed.get("commands", [])
            if not commands:
                # No commands to execute, treat as respond
                conv.messages.append({"role": "assistant", "content": claude_response})
                return {
                    "conversation_id": conv.conversation_id,
                    "response": parsed.get("message", claude_response),
                    "commands_executed": commands_this_turn
                }

            # Execute each command and collect results
            results = []
            for cmd in commands:
                try:
                    result = await execute_kubectl(cmd)
                    commands_this_turn.append(f"kubectl {cmd}")
                    conv.commands_executed.append(f"kubectl {cmd}")

                    result_text = f"Command: kubectl {cmd}\n"
                    if result.get("return_code") == 0:
                        result_text += f"Output:\n{result.get('stdout', '(no output)')}"
                    else:
                        result_text += f"Error (exit code {result.get('return_code')}):\n"
                        result_text += result.get("stderr") or result.get("stdout") or "(no output)"
                    results.append(result_text)

                except httpx.HTTPError as e:
                    results.append(f"Command: kubectl {cmd}\nError: Failed to execute - {str(e)}")

            # Add command results to conversation
            results_message = "Command execution results:\n\n" + "\n\n---\n\n".join(results)
            conv.messages.append({"role": "assistant", "content": claude_response})
            conv.messages.append({"role": "user", "content": results_message})

            # Continue loop to let Claude interpret results

        elif action == "respond":
            # Final response
            message = parsed.get("message", claude_response)
            conv.messages.append({"role": "assistant", "content": message})

            return {
                "conversation_id": conv.conversation_id,
                "response": message,
                "commands_executed": commands_this_turn
            }

        else:
            # Unknown action, treat as response
            conv.messages.append({"role": "assistant", "content": claude_response})
            return {
                "conversation_id": conv.conversation_id,
                "response": claude_response,
                "commands_executed": commands_this_turn
            }

    # Max iterations reached
    return {
        "conversation_id": conv.conversation_id,
        "response": "I've reached the maximum number of steps for this request. Please try a simpler question.",
        "commands_executed": commands_this_turn,
        "error": True
    }


def clear_conversation(conversation_id: str) -> bool:
    """Clear a conversation from memory."""
    if conversation_id in conversations:
        del conversations[conversation_id]
        return True
    return False

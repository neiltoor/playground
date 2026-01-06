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
MAX_AGENT_ITERATIONS = 15
COMMAND_TIMEOUT = 120  # Increased for helm operations

SYSTEM_PROMPT = """You are a Kubernetes assistant with access to kubectl and helm commands. Help users understand and manage their Kubernetes cluster.

You have THREE actions available:

1. **Execute commands** (kubectl or helm):
{"action": "execute", "commands": ["kubectl get pods -n default", "helm list -A"]}

2. **Fetch a URL** (to read documentation, GitHub repos, helm chart info):
{"action": "fetch", "url": "https://example.com/path"}

3. **Respond to the user** (final answer):
{"action": "respond", "message": "Your helpful response here"}

IMPORTANT RULES:
- Commands MUST include the tool prefix: "kubectl ..." or "helm ..."
- You can run multiple commands in one request
- Use fetch to read GitHub repos, documentation, or chart values before installing
- After command results or fetch results, interpret them for the user
- For helm installs, ALWAYS check if the repo is added first, add it if needed

KUBECTL EXAMPLES:
- "kubectl get pods -n default"
- "kubectl get pods -A"
- "kubectl describe pod my-pod -n default"
- "kubectl get deployments -o wide"
- "kubectl logs my-pod -n default --tail=50"
- "kubectl get nodes"
- "kubectl get events --sort-by='.lastTimestamp'"

HELM EXAMPLES:
- "helm list -A" (list all releases)
- "helm repo list" (list added repos)
- "helm repo add prometheus-community https://prometheus-community.github.io/helm-charts"
- "helm repo update"
- "helm search repo prometheus"
- "helm install my-release repo/chart -n namespace --create-namespace"
- "helm upgrade my-release repo/chart -n namespace"
- "helm uninstall my-release -n namespace"
- "helm show values repo/chart" (see default values)

WORKFLOW FOR HELM INSTALLS:
1. If user provides a GitHub URL, fetch it to understand the chart
2. Check if repo is added: "helm repo list"
3. Add repo if needed: "helm repo add name url"
4. Update repos: "helm repo update"
5. Search for chart: "helm search repo chartname"
6. Install: "helm install releasename repo/chart -n namespace --create-namespace"

Always explain what you're doing and interpret results in plain language.
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


async def execute_command(command: str) -> Dict[str, Any]:
    """Execute a kubectl or helm command via kubectl-service."""
    async with httpx.AsyncClient(timeout=COMMAND_TIMEOUT + 10) as client:
        response = await client.post(
            f"{KUBECTL_SERVICE_URL}/run",
            json={
                "command": command,
                "timeout": COMMAND_TIMEOUT
            }
        )
        response.raise_for_status()
        return response.json()


async def fetch_url(url: str) -> str:
    """Fetch content from a URL (for GitHub repos, docs, etc.)."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            # For GitHub repos, try to get the README
            if "github.com" in url and "/tree/" in url:
                # Convert tree URL to raw README URL
                # https://github.com/owner/repo/tree/main/path -> raw README
                parts = url.replace("https://github.com/", "").split("/tree/")
                if len(parts) == 2:
                    repo = parts[0]
                    branch_path = parts[1].split("/", 1)
                    branch = branch_path[0]
                    path = branch_path[1] if len(branch_path) > 1 else ""
                    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}/README.md"
                    response = await client.get(raw_url)
                    if response.status_code == 200:
                        content = response.text
                        # Truncate if too long
                        if len(content) > 8000:
                            content = content[:8000] + "\n\n[Content truncated...]"
                        return f"README.md from {url}:\n\n{content}"

            # For regular URLs, just fetch the content
            response = await client.get(url)
            response.raise_for_status()

            content = response.text
            # Truncate if too long
            if len(content) > 8000:
                content = content[:8000] + "\n\n[Content truncated...]"
            return content

        except Exception as e:
            return f"Error fetching URL: {str(e)}"


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
                    result = await execute_command(cmd)
                    commands_this_turn.append(cmd)
                    conv.commands_executed.append(cmd)

                    result_text = f"Command: {cmd}\n"
                    if result.get("return_code") == 0:
                        result_text += f"Output:\n{result.get('stdout', '(no output)')}"
                    else:
                        result_text += f"Error (exit code {result.get('return_code')}):\n"
                        result_text += result.get("stderr") or result.get("stdout") or "(no output)"
                    results.append(result_text)

                except httpx.HTTPError as e:
                    results.append(f"Command: {cmd}\nError: Failed to execute - {str(e)}")

            # Add command results to conversation
            results_message = "Command execution results:\n\n" + "\n\n---\n\n".join(results)
            conv.messages.append({"role": "assistant", "content": claude_response})
            conv.messages.append({"role": "user", "content": results_message})

            # Continue loop to let Claude interpret results

        elif action == "fetch":
            url = parsed.get("url", "")
            if not url:
                conv.messages.append({"role": "assistant", "content": claude_response})
                return {
                    "conversation_id": conv.conversation_id,
                    "response": "No URL provided to fetch.",
                    "commands_executed": commands_this_turn,
                    "error": True
                }

            # Fetch the URL
            try:
                fetch_result = await fetch_url(url)
                fetch_message = f"Fetched content from {url}:\n\n{fetch_result}"
            except Exception as e:
                fetch_message = f"Error fetching {url}: {str(e)}"

            # Add fetch results to conversation
            conv.messages.append({"role": "assistant", "content": claude_response})
            conv.messages.append({"role": "user", "content": fetch_message})

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

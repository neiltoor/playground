/**
 * Kubectl Agent - Chat interface for Kubernetes cluster management
 * With streaming support for real-time progress updates
 */

// State
let conversationId = null;
let isLoading = false;

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const sendBtnText = document.getElementById('sendBtnText');
const sendBtnSpinner = document.getElementById('sendBtnSpinner');
const welcomeMessage = document.getElementById('welcomeMessage');
const usernameDisplay = document.getElementById('usernameDisplay');

// Check authentication on load
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
        window.location.href = '/login.html';
        return;
    }

    const username = localStorage.getItem('username');
    if (username && usernameDisplay) {
        usernameDisplay.textContent = username;
    }

    // Auto-resize textarea
    messageInput.addEventListener('input', autoResizeTextarea);

    // Handle Enter key (Shift+Enter for new line)
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
});

// Form submission
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const message = messageInput.value.trim();
    if (!message || isLoading) return;

    await sendMessageStreaming(message);
});

/**
 * Send a message using streaming endpoint
 */
async function sendMessageStreaming(message) {
    isLoading = true;
    setLoading(true);

    // Hide welcome message
    if (welcomeMessage) {
        welcomeMessage.style.display = 'none';
    }

    // Add user message to chat
    addMessage('user', message);

    // Clear input
    messageInput.value = '';
    autoResizeTextarea();

    // Create a progress container for streaming updates
    const progressContainer = addProgressContainer();
    let commandsExecuted = [];

    try {
        const response = await fetch('/api/kubectl-agent/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE messages
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const event = JSON.parse(line.slice(6));
                        handleStreamEvent(event, progressContainer, commandsExecuted);

                        // If this is the final response, update conversation ID
                        if (event.type === 'response') {
                            conversationId = event.conversation_id;
                            commandsExecuted = event.commands_executed || [];
                        }
                    } catch (e) {
                        console.error('Error parsing SSE event:', e);
                    }
                }
            }
        }

    } catch (error) {
        progressContainer.remove();
        addMessage('error', `Error: ${error.message}`);
        console.error('Chat error:', error);
    } finally {
        isLoading = false;
        setLoading(false);
    }
}

/**
 * Handle a streaming event
 */
function handleStreamEvent(event, progressContainer, commandsExecuted) {
    switch (event.type) {
        case 'thinking':
            updateProgress(progressContainer, 'thinking', event.message);
            // Add thinking as a visible step (skip generic "Processing request...")
            if (event.message && event.message !== 'Processing request...') {
                addThinkingStep(progressContainer, event.message);
            }
            break;

        case 'executing':
            updateProgress(progressContainer, 'executing', `Running: ${event.command}`);
            addCommandStep(progressContainer, event.command, 'running');
            break;

        case 'result':
            updateCommandStep(progressContainer, event.command, event.success, event.output);
            break;

        case 'fetching':
            updateProgress(progressContainer, 'fetching', `Fetching: ${event.url}`);
            addCommandStep(progressContainer, `Fetching ${event.url}`, 'running');
            break;

        case 'response':
            // Keep progress steps but remove the spinner, then add final response
            const spinner = progressContainer.querySelector('.progress-status');
            if (spinner) spinner.remove();

            // Mark container as complete
            progressContainer.classList.add('complete');

            // Add final response message
            addMessage('assistant', event.message, event.commands_executed);
            if (event.error) {
                addMessage('system', 'Note: The agent encountered an issue processing your request.');
            }
            break;

        case 'error':
            updateProgress(progressContainer, 'error', event.message);
            break;
    }
}

/**
 * Add a progress container for streaming updates
 */
function addProgressContainer() {
    const container = document.createElement('div');
    container.className = 'progress-container';
    container.innerHTML = `
        <div class="progress-status">
            <div class="progress-spinner"></div>
            <span class="progress-text">Starting...</span>
        </div>
        <div class="progress-steps"></div>
    `;
    chatMessages.appendChild(container);
    scrollToBottom();
    return container;
}

/**
 * Update progress status
 */
function updateProgress(container, type, message) {
    const statusEl = container.querySelector('.progress-text');
    if (statusEl) {
        statusEl.textContent = message;
    }
    scrollToBottom();
}

/**
 * Add a thinking step to show agent reasoning
 */
function addThinkingStep(container, message) {
    const stepsEl = container.querySelector('.progress-steps');
    if (stepsEl) {
        const step = document.createElement('div');
        step.className = 'progress-step thinking';
        step.innerHTML = `
            <span class="step-icon">💭</span>
            <span class="step-thinking">${escapeHtml(message)}</span>
        `;
        stepsEl.appendChild(step);
        scrollToBottom();
    }
}

/**
 * Add a command step to the progress
 */
function addCommandStep(container, command, status) {
    const stepsEl = container.querySelector('.progress-steps');
    if (stepsEl) {
        const step = document.createElement('div');
        step.className = `progress-step ${status}`;
        step.dataset.command = command;
        step.innerHTML = `
            <span class="step-icon">${status === 'running' ? '⏳' : '✓'}</span>
            <code class="step-command">${escapeHtml(command)}</code>
            <div class="step-output"></div>
        `;
        stepsEl.appendChild(step);
        scrollToBottom();
    }
}

/**
 * Update a command step with result
 */
function updateCommandStep(container, command, success, output) {
    const stepsEl = container.querySelector('.progress-steps');
    if (stepsEl) {
        // Find the step by command
        const steps = stepsEl.querySelectorAll('.progress-step');
        for (const step of steps) {
            if (step.dataset.command === command || step.dataset.command === `Fetching ${command.replace('fetch ', '')}`) {
                step.className = `progress-step ${success ? 'success' : 'error'}`;
                step.querySelector('.step-icon').textContent = success ? '✓' : '✗';

                if (output) {
                    const outputEl = step.querySelector('.step-output');
                    outputEl.innerHTML = `<pre>${escapeHtml(output)}</pre>`;
                }
                break;
            }
        }
        scrollToBottom();
    }
}

/**
 * Add a message to the chat
 */
function addMessage(role, content, commandsExecuted = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    // Format content (handle code blocks and newlines)
    let formattedContent = escapeHtml(content);

    // Convert markdown-style code blocks
    formattedContent = formattedContent.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

    // Convert inline code
    formattedContent = formattedContent.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Convert **bold** to <strong>
    formattedContent = formattedContent.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Convert newlines to <br>
    formattedContent = formattedContent.replace(/\n/g, '<br>');

    messageDiv.innerHTML = formattedContent;

    // Add commands executed if any
    if (commandsExecuted && commandsExecuted.length > 0) {
        const commandsDiv = document.createElement('div');
        commandsDiv.className = 'commands-executed';
        commandsDiv.innerHTML = `<strong>Commands executed:</strong>`;
        commandsExecuted.forEach(cmd => {
            const codeEl = document.createElement('code');
            codeEl.textContent = cmd;
            commandsDiv.appendChild(codeEl);
        });
        messageDiv.appendChild(commandsDiv);
    }

    chatMessages.appendChild(messageDiv);
    scrollToBottom();

    return messageDiv;
}

/**
 * Add typing indicator (fallback for non-streaming)
 */
function addTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<span></span><span></span><span></span>';
    chatMessages.appendChild(indicator);
    scrollToBottom();
    return indicator;
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Set loading state
 */
function setLoading(loading) {
    sendBtn.disabled = loading;
    messageInput.disabled = loading;
    sendBtnText.style.display = loading ? 'none' : 'inline';
    sendBtnSpinner.style.display = loading ? 'inline-block' : 'none';
}

/**
 * Auto-resize textarea
 */
function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
}

/**
 * Use example query
 */
function useExample(element) {
    messageInput.value = element.textContent;
    messageInput.focus();
    autoResizeTextarea();
}

/**
 * Start new chat
 */
function startNewChat() {
    conversationId = null;

    // Clear messages
    chatMessages.innerHTML = '';

    // Show welcome message
    chatMessages.innerHTML = `
        <div class="welcome-message" id="welcomeMessage">
            <h2>Welcome to Kubectl Agent</h2>
            <p>Ask me anything about your Kubernetes cluster.</p>
            <p>I can run kubectl and helm commands to help you manage your cluster.</p>
            <div class="example-queries">
                <span class="example-query" onclick="useExample(this)">Show all pods</span>
                <span class="example-query" onclick="useExample(this)">What nodes are in the cluster?</span>
                <span class="example-query" onclick="useExample(this)">List all helm releases</span>
                <span class="example-query" onclick="useExample(this)">Show recent events</span>
            </div>
        </div>
    `;

    messageInput.value = '';
    messageInput.focus();
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Logout function
 */
function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    window.location.href = '/login.html';
}

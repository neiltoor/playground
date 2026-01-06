/**
 * Kubectl Agent - Chat interface for Kubernetes cluster management
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

    await sendMessage(message);
});

/**
 * Send a message to the kubectl agent
 */
async function sendMessage(message) {
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

    // Show typing indicator
    const typingIndicator = addTypingIndicator();

    try {
        const response = await fetch('/api/kubectl-agent/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId
            })
        });

        // Remove typing indicator
        typingIndicator.remove();

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get response');
        }

        const data = await response.json();

        // Update conversation ID
        conversationId = data.conversation_id;

        // Add assistant response
        addMessage('assistant', data.response, data.commands_executed);

        if (data.error) {
            addMessage('system', 'Note: The agent encountered an issue processing your request.');
        }

    } catch (error) {
        typingIndicator.remove();
        addMessage('error', `Error: ${error.message}`);
        console.error('Chat error:', error);
    } finally {
        isLoading = false;
        setLoading(false);
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
 * Add typing indicator
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
            <p>I can run kubectl commands to get information and help you understand your cluster.</p>
            <div class="example-queries">
                <span class="example-query" onclick="useExample(this)">Show all pods</span>
                <span class="example-query" onclick="useExample(this)">What nodes are in the cluster?</span>
                <span class="example-query" onclick="useExample(this)">Are there any failing pods?</span>
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

// API Configuration
const API_BASE_URL = '/api';

// Storage keys
const AUTH_TOKEN_KEY = 'auth_token';
const USERNAME_KEY = 'username';

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const documentsList = document.getElementById('documentsList');
const messagesContainer = document.getElementById('messagesContainer');
const queryForm = document.getElementById('queryForm');
const queryInput = document.getElementById('queryInput');
const sendBtn = document.getElementById('sendBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const providerSelect = document.getElementById('providerSelect');
const modelDisplay = document.getElementById('modelDisplay');

// State
let uploadedDocuments = [];

// LLM Provider Configuration
const LLM_MODELS = {
    openrouter: 'anthropic/claude-3-haiku',
    anthropic: 'claude-3-haiku-20240307'
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuthentication();
    initializeEventListeners();
    loadDocuments();
});

function checkAuthentication() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) {
        // Redirect to login
        window.location.href = '/login.html';
        return;
    }

    // Display username in header
    const username = localStorage.getItem(USERNAME_KEY);
    if (username) {
        displayUserInfo(username);
    }
}

function displayUserInfo(username) {
    // Add user info to header
    const header = document.querySelector('header');
    if (header) {
        const userDiv = document.createElement('div');
        userDiv.className = 'user-info';
        userDiv.innerHTML = `
            <span>Logged in as: <strong>${escapeHtml(username)}</strong></span>
            <button class="btn btn-secondary" onclick="logout()">Logout</button>
        `;
        header.appendChild(userDiv);
    }
}

function logout() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    window.location.href = '/login.html';
}

function getAuthHeaders() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    return {
        'Authorization': `Bearer ${token}`
    };
}

function handleAuthError() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    window.location.href = '/login.html';
}

function initializeEventListeners() {
    // Browse button
    browseBtn.addEventListener('click', () => fileInput.click());

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');

        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    // Click to upload
    uploadArea.addEventListener('click', (e) => {
        if (e.target === uploadArea || e.target.closest('.upload-icon, p')) {
            fileInput.click();
        }
    });

    // Provider selection change
    providerSelect.addEventListener('change', (e) => {
        const provider = e.target.value;
        const model = LLM_MODELS[provider];
        modelDisplay.textContent = model;
    });

    // Query form
    queryForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleQuery();
    });

    // Enter to submit (Shift+Enter for new line)
    queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleQuery();
        }
    });
}

async function handleFileUpload(file) {
    // Validate file
    const allowedExtensions = ['.pdf', '.txt', '.docx', '.md'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();

    if (!allowedExtensions.includes(fileExt)) {
        showError(`File type not supported. Allowed: ${allowedExtensions.join(', ')}`);
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showError('File size exceeds 10MB limit');
        return;
    }

    showLoading('Uploading and processing document...');

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: formData
        });

        // Handle authentication error
        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const result = await response.json();

        hideLoading();
        showSuccess(`Resume "${result.filename}" uploaded successfully! Ready for comparison.`);

        // Add to uploaded documents
        uploadedDocuments.push({
            id: result.document_id,
            filename: result.filename,
            chunks: result.chunks_created
        });

        updateDocumentsList();
        fileInput.value = '';

    } catch (error) {
        hideLoading();
        showError(`Upload failed: ${error.message}`);
    }
}

async function handleQuery() {
    const query = queryInput.value.trim();

    if (!query) return;

    // Allow queries even with just the baseline (Neil's resume)
    // if (uploadedDocuments.length === 0) {
    //     showError('Please upload at least one resume before comparing');
    //     return;
    // }

    // Get selected provider and model
    const provider = providerSelect.value;
    const model = LLM_MODELS[provider];

    // Disable input
    queryInput.disabled = true;
    sendBtn.disabled = true;

    // Add user message
    addMessage(query, 'user');
    queryInput.value = '';

    // Show loading
    const loadingMessage = addLoadingMessage();

    try {
        const authHeaders = getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: {
                ...authHeaders,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                top_k: 5,
                provider: provider,
                model: model
            })
        });

        // Handle authentication error
        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Query failed');
        }

        const result = await response.json();

        // Remove loading message
        loadingMessage.remove();

        // Add assistant response
        addMessage(result.answer, 'assistant', result.sources);

    } catch (error) {
        loadingMessage.remove();
        showError(`Query failed: ${error.message}`);
    } finally {
        // Re-enable input
        queryInput.disabled = false;
        sendBtn.disabled = false;
        queryInput.focus();
    }
}

async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents`, {
            headers: getAuthHeaders()
        });

        // Handle authentication error
        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (response.ok) {
            const documents = await response.json();
            uploadedDocuments = documents;
            updateDocumentsList();
        }
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

function updateDocumentsList() {
    if (uploadedDocuments.length === 0) {
        documentsList.innerHTML = '<p class="no-documents">No resumes uploaded yet</p>';
        return;
    }

    documentsList.innerHTML = uploadedDocuments.map(doc => `
        <div class="document-item">
            <div>
                <div class="document-name">
                    ${escapeHtml(doc.filename)}
                    ${doc.is_shared ? '<span class="shared-badge">Baseline</span>' : ''}
                </div>
                <div class="document-meta">${doc.chunk_count || 0} chunks</div>
            </div>
        </div>
    `).join('');
}

function addMessage(text, type, sources = null) {
    // Remove welcome message if it exists
    const welcomeMessage = messagesContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    const label = type === 'user' ? 'You' : 'Assistant';

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        sourcesHtml = `
            <div class="message-sources">
                <h4>Sources</h4>
                ${sources.map(source => `
                    <div class="source-item">
                        <div class="source-filename">${escapeHtml(source.filename || 'Unknown')}</div>
                        <div class="source-text">${escapeHtml(truncateText(source.text, 150))}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    messageDiv.innerHTML = `
        <div class="message-label">${label}</div>
        <div class="message-content">
            ${formatMessageText(text)}
            ${sourcesHtml}
        </div>
    `;

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return messageDiv;
}

function addLoadingMessage() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-message';
    loadingDiv.innerHTML = `
        <div class="message-label">Assistant</div>
        <div class="message-content">
            <span>Thinking</span>
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(loadingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return loadingDiv;
}

function showLoading(message = 'Processing...') {
    loadingOverlay.querySelector('p').textContent = message;
    loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    loadingOverlay.classList.add('hidden');
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;

    const uploadPanel = document.querySelector('.upload-panel');
    uploadPanel.insertBefore(errorDiv, uploadPanel.firstChild);

    setTimeout(() => errorDiv.remove(), 5000);
}

function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.textContent = message;

    const uploadPanel = document.querySelector('.upload-panel');
    uploadPanel.insertBefore(successDiv, uploadPanel.firstChild);

    setTimeout(() => successDiv.remove(), 5000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatMessageText(text) {
    // Escape HTML first
    let formatted = escapeHtml(text);

    // Convert markdown-style bold **text** to <strong>
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Convert markdown-style italic *text* to <em>
    formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Convert line breaks to <br>
    formatted = formatted.replace(/\n/g, '<br>');

    // Convert bullet points (lines starting with - or *)
    formatted = formatted.replace(/^[\-\*]\s+(.+)$/gm, '<li>$1</li>');

    // Wrap consecutive list items in <ul>
    formatted = formatted.replace(/(<li>.*<\/li>(?:<br>)?)+/g, (match) => {
        // Remove <br> tags between list items
        const cleaned = match.replace(/<br>/g, '');
        return '<ul>' + cleaned + '</ul>';
    });

    // Add spacing after headers (lines ending with :)
    formatted = formatted.replace(/^(.+:)<br>/gm, '<div class="text-header">$1</div>');

    return formatted;
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

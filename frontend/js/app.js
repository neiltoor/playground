// API Configuration
const API_BASE_URL = '/api';

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

// State
let uploadedDocuments = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    loadDocuments();
});

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
        uploadArea.classList.add('dragging');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragging');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragging');

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
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const result = await response.json();

        hideLoading();
        showSuccess(`Document "${result.filename}" uploaded successfully! Created ${result.chunks_created} chunks.`);

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

    if (uploadedDocuments.length === 0) {
        showError('Please upload at least one document before asking questions');
        return;
    }

    // Disable input
    queryInput.disabled = true;
    sendBtn.disabled = true;

    // Add user message
    addMessage(query, 'user');
    queryInput.value = '';

    // Show loading
    const loadingMessage = addLoadingMessage();

    try {
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                top_k: 5
            })
        });

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
        const response = await fetch(`${API_BASE_URL}/documents`);

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
        documentsList.innerHTML = '<p class="no-documents">No documents uploaded yet</p>';
        return;
    }

    documentsList.innerHTML = uploadedDocuments.map(doc => `
        <div class="document-item">
            <div>
                <div class="document-name">${escapeHtml(doc.filename)}</div>
                <div class="document-meta">${doc.chunks || 0} chunks</div>
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
    messageDiv.className = `message message-${type}`;

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        sourcesHtml = `
            <div class="message-sources">
                <h4>Sources:</h4>
                ${sources.map(source => `
                    <div class="source-item">
                        <div class="source-filename">${escapeHtml(source.filename || 'Unknown')}</div>
                        <div class="source-text">${escapeHtml(truncateText(source.text, 150))}</div>
                        <div class="source-score">Relevance: ${(source.score * 100).toFixed(1)}%</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    messageDiv.innerHTML = `
        <div class="message-bubble">
            ${escapeHtml(text)}
            ${sourcesHtml}
        </div>
    `;

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return messageDiv;
}

function addLoadingMessage() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message message-assistant';
    loadingDiv.innerHTML = `
        <div class="message-bubble">
            <em>Thinking...</em>
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

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

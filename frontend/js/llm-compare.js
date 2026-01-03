// API Configuration
const API_BASE_URL = '/api';

// Storage keys
const AUTH_TOKEN_KEY = 'auth_token';
const USERNAME_KEY = 'username';

// DOM Elements
const compareForm = document.getElementById('compareForm');
const promptInput = document.getElementById('promptInput');
const compareBtn = document.getElementById('compareBtn');
const compareBtnText = document.getElementById('compareBtnText');
const compareBtnSpinner = document.getElementById('compareBtnSpinner');
const resultsSection = document.getElementById('resultsSection');
const errorMessage = document.getElementById('errorMessage');

// Result elements
const anthropicContent = document.getElementById('anthropicContent');
const anthropicModel = document.getElementById('anthropicModel');
const anthropicTokens = document.getElementById('anthropicTokens');
const openrouterContent = document.getElementById('openrouterContent');
const openrouterModel = document.getElementById('openrouterModel');
const openrouterTokens = document.getElementById('openrouterTokens');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuthentication();
    initializeEventListeners();
});

function checkAuthentication() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) {
        window.location.href = '/login.html';
        return;
    }

    // Display username
    const username = localStorage.getItem(USERNAME_KEY);
    if (username) {
        const usernameDisplay = document.getElementById('usernameDisplay');
        if (usernameDisplay) {
            usernameDisplay.textContent = username;
        }
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
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

function handleAuthError() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    window.location.href = '/login.html';
}

function initializeEventListeners() {
    compareForm.addEventListener('submit', handleCompare);
}

async function handleCompare(e) {
    e.preventDefault();

    const prompt = promptInput.value.trim();
    if (!prompt) return;

    // Hide error, show loading
    errorMessage.style.display = 'none';
    setLoading(true);

    // Show results section with loading state
    resultsSection.style.display = 'grid';
    anthropicContent.innerHTML = '<p class="loading-text">Generating response...</p>';
    openrouterContent.innerHTML = '<p class="loading-text">Generating response...</p>';
    anthropicTokens.textContent = '-';
    openrouterTokens.textContent = '-';

    try {
        const response = await fetch(`${API_BASE_URL}/llm-compare`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                prompt: prompt,
                anthropic_model: 'claude-3-haiku-20240307',
                openrouter_model: 'x-ai/grok-3-mini'
            })
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Comparison failed');
        }

        const data = await response.json();
        displayResults(data);

    } catch (error) {
        errorMessage.textContent = error.message;
        errorMessage.style.display = 'block';
        resultsSection.style.display = 'none';
    } finally {
        setLoading(false);
    }
}

function displayResults(data) {
    // Anthropic result
    if (data.anthropic.error) {
        anthropicContent.innerHTML = `<p class="error-text">${escapeHtml(data.anthropic.error)}</p>`;
    } else {
        anthropicContent.innerHTML = `<div class="response-text">${formatResponse(data.anthropic.content)}</div>`;
    }
    anthropicModel.textContent = data.anthropic.model || 'claude-3-haiku';
    anthropicTokens.textContent = formatTokens(data.anthropic.usage);

    // OpenRouter result
    if (data.openrouter.error) {
        openrouterContent.innerHTML = `<p class="error-text">${escapeHtml(data.openrouter.error)}</p>`;
    } else {
        openrouterContent.innerHTML = `<div class="response-text">${formatResponse(data.openrouter.content)}</div>`;
    }
    openrouterModel.textContent = data.openrouter.model || 'grok-3-mini';
    openrouterTokens.textContent = formatTokens(data.openrouter.usage);
}

function formatResponse(text) {
    if (!text) return '<p class="placeholder">No response</p>';
    // Convert newlines to paragraphs and escape HTML
    return text
        .split('\n\n')
        .map(para => `<p>${escapeHtml(para).replace(/\n/g, '<br>')}</p>`)
        .join('');
}

function formatTokens(usage) {
    if (!usage) return '-';
    const input = usage.input_tokens || 0;
    const output = usage.output_tokens || 0;
    return `${input} in / ${output} out`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function setLoading(loading) {
    compareBtn.disabled = loading;
    compareBtnText.style.display = loading ? 'none' : 'inline';
    compareBtnSpinner.style.display = loading ? 'inline-block' : 'none';
}

// Request Login Page JavaScript

// API Configuration
const API_BASE_URL = '/api';

// State
let currentCaptchaId = null;

// DOM Elements
const requestForm = document.getElementById('requestForm');
const errorMessage = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');
const submitBtn = document.getElementById('submitBtn');
const submitBtnText = document.getElementById('submitBtnText');
const submitBtnSpinner = document.getElementById('submitBtnSpinner');
const captchaQuestion = document.getElementById('captchaQuestion');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadCaptcha();
});

async function loadCaptcha() {
    try {
        captchaQuestion.textContent = 'Loading...';
        const response = await fetch(`${API_BASE_URL}/captcha`);
        if (!response.ok) throw new Error('Failed to load CAPTCHA');

        const data = await response.json();
        currentCaptchaId = data.challenge_id;
        captchaQuestion.textContent = data.question;
    } catch (error) {
        captchaQuestion.textContent = 'Error loading. Click refresh.';
        console.error('Error loading CAPTCHA:', error);
    }
}

function refreshCaptcha() {
    document.getElementById('captchaAnswer').value = '';
    loadCaptcha();
}

// Make refreshCaptcha available globally for onclick handler
window.refreshCaptcha = refreshCaptcha;

requestForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = document.getElementById('email').value.trim();
    const reason = document.getElementById('reason').value.trim();
    const captchaAnswer = document.getElementById('captchaAnswer').value.trim();

    // Hide previous messages
    errorMessage.style.display = 'none';
    successMessage.style.display = 'none';

    // Validate
    if (!email || !reason || !captchaAnswer) {
        errorMessage.textContent = 'Please fill in all fields.';
        errorMessage.style.display = 'block';
        return;
    }

    if (reason.length < 10) {
        errorMessage.textContent = 'Please provide a more detailed reason (at least 10 characters).';
        errorMessage.style.display = 'block';
        return;
    }

    // Show loading
    submitBtn.disabled = true;
    submitBtnText.style.display = 'none';
    submitBtnSpinner.style.display = 'inline-block';

    try {
        const response = await fetch(`${API_BASE_URL}/request-login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: email,
                reason: reason,
                captcha_id: currentCaptchaId,
                captcha_answer: captchaAnswer
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Request failed');
        }

        const data = await response.json();

        // Show success
        successMessage.textContent = data.message;
        successMessage.style.display = 'block';
        requestForm.reset();

        // Refresh CAPTCHA for potential retry
        loadCaptcha();

    } catch (error) {
        errorMessage.textContent = error.message;
        errorMessage.style.display = 'block';

        // Refresh CAPTCHA on error
        loadCaptcha();
    } finally {
        submitBtn.disabled = false;
        submitBtnText.style.display = 'inline';
        submitBtnSpinner.style.display = 'none';
    }
});

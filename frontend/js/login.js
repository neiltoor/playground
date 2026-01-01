// API Configuration
const API_BASE_URL = '/api';

// Storage keys
const AUTH_TOKEN_KEY = 'auth_token';
const USERNAME_KEY = 'username';

// DOM Elements
const loginForm = document.getElementById('loginForm');
const errorMessage = document.getElementById('errorMessage');
const loginBtn = document.getElementById('loginBtn');
const loginBtnText = document.getElementById('loginBtnText');
const loginBtnSpinner = document.getElementById('loginBtnSpinner');

// Check if already logged in
if (localStorage.getItem(AUTH_TOKEN_KEY)) {
    window.location.href = '/';
}

// Handle login form submission
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    // Hide previous errors
    errorMessage.style.display = 'none';

    // Show loading state
    loginBtn.disabled = true;
    loginBtnText.style.display = 'none';
    loginBtnSpinner.style.display = 'inline-block';

    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();

        // Store token and username
        localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
        localStorage.setItem(USERNAME_KEY, data.username);

        // Redirect to main app
        window.location.href = '/';

    } catch (error) {
        // Show error message
        errorMessage.textContent = error.message;
        errorMessage.style.display = 'block';

        // Reset loading state
        loginBtn.disabled = false;
        loginBtnText.style.display = 'inline';
        loginBtnSpinner.style.display = 'none';
    }
});

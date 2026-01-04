// Storage keys
const AUTH_TOKEN_KEY = 'auth_token';
const USERNAME_KEY = 'username';
const USER_ROLE_KEY = 'user_role';

// Check authentication on page load
document.addEventListener('DOMContentLoaded', () => {
    checkAuthentication();
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

    // Show admin card if user is admin
    const role = localStorage.getItem(USER_ROLE_KEY);
    if (role === 'admin') {
        const adminCard = document.getElementById('adminCard');
        if (adminCard) {
            adminCard.style.display = 'flex';
        }
    }
}

function logout() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    localStorage.removeItem(USER_ROLE_KEY);
    window.location.href = '/login.html';
}

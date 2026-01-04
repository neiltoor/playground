// API Configuration
const API_BASE_URL = '/api';

// Storage keys
const AUTH_TOKEN_KEY = 'auth_token';
const USERNAME_KEY = 'username';
const USER_ROLE_KEY = 'user_role';

// Pagination state
let currentPage = 1;
const pageSize = 50;
let totalItems = 0;
let currentFilters = {};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAdminAccess();
    loadStats();
    loadActivityLogs();
});

function checkAdminAccess() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    const role = localStorage.getItem(USER_ROLE_KEY);

    if (!token) {
        window.location.href = '/login.html';
        return;
    }

    if (role !== 'admin') {
        alert('Admin access required');
        window.location.href = '/landing.html';
        return;
    }

    // Display username
    const username = localStorage.getItem(USERNAME_KEY);
    if (username) {
        document.getElementById('usernameDisplay').textContent = username;
    }
}

function logout() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    localStorage.removeItem(USER_ROLE_KEY);
    window.location.href = '/login.html';
}

function getAuthHeaders() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/activity/stats`, {
            headers: getAuthHeaders()
        });

        if (response.status === 401 || response.status === 403) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to load stats');
        }

        const stats = await response.json();

        // Update stat cards
        document.getElementById('loginCount').textContent = stats.by_type?.login || 0;
        document.getElementById('apiCallCount').textContent = stats.by_type?.api_call || 0;
        document.getElementById('activeUserCount').textContent = stats.unique_users_today || 0;
        document.getElementById('totalCount').textContent = stats.last_24_hours || 0;

    } catch (error) {
        console.error('Error loading stats:', error);
        showError('Failed to load activity statistics');
    }
}

async function loadActivityLogs() {
    try {
        const offset = (currentPage - 1) * pageSize;
        let url = `${API_BASE_URL}/activity?limit=${pageSize}&offset=${offset}`;

        // Add filters
        if (currentFilters.username) {
            url += `&username=${encodeURIComponent(currentFilters.username)}`;
        }
        if (currentFilters.activity_type) {
            url += `&activity_type=${encodeURIComponent(currentFilters.activity_type)}`;
        }

        const response = await fetch(url, {
            headers: getAuthHeaders()
        });

        if (response.status === 401 || response.status === 403) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to load activity logs');
        }

        const data = await response.json();
        totalItems = data.total;
        renderActivityTable(data.logs);
        updatePagination();

    } catch (error) {
        console.error('Error loading activity logs:', error);
        showError('Failed to load activity logs');
        document.getElementById('activityTableBody').innerHTML =
            '<tr><td colspan="6" class="no-data">Error loading data</td></tr>';
    }
}

function renderActivityTable(logs) {
    const tbody = document.getElementById('activityTableBody');

    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="no-data">No activity logs found</td></tr>';
        return;
    }

    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>${formatTimestamp(log.timestamp)}</td>
            <td><span class="username-badge">${escapeHtml(log.username)}</span></td>
            <td><span class="type-badge type-${log.activity_type}">${formatActivityType(log.activity_type)}</span></td>
            <td class="resource-cell" title="${escapeHtml(log.resource_path || '-')}">${escapeHtml(log.resource_path || '-')}</td>
            <td><code>${escapeHtml(log.ip_address || '-')}</code></td>
            <td class="details-cell">${formatDetails(log.details)}</td>
        </tr>
    `).join('');
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

function formatActivityType(type) {
    const types = {
        'login': 'Login',
        'api_call': 'API Call',
        'page_visit': 'Page Visit',
        'logout': 'Logout'
    };
    return types[type] || type;
}

function formatDetails(details) {
    if (!details) return '-';
    try {
        const parsed = JSON.parse(details);
        if (parsed.success !== undefined) {
            return parsed.success ?
                '<span class="success-badge">Success</span>' :
                '<span class="failure-badge">Failed</span>';
        }
        if (parsed.method && parsed.status_code) {
            const statusClass = parsed.status_code >= 400 ? 'failure-badge' : 'success-badge';
            return `<span class="method-badge">${parsed.method}</span> <span class="${statusClass}">${parsed.status_code}</span>`;
        }
        return `<code>${JSON.stringify(parsed)}</code>`;
    } catch {
        return escapeHtml(details);
    }
}

function updatePagination() {
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
    document.getElementById('currentPage').textContent = currentPage;
    document.getElementById('totalPages').textContent = totalPages;
    document.getElementById('prevBtn').disabled = currentPage === 1;
    document.getElementById('nextBtn').disabled = currentPage >= totalPages;
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        loadActivityLogs();
    }
}

function nextPage() {
    const totalPages = Math.ceil(totalItems / pageSize);
    if (currentPage < totalPages) {
        currentPage++;
        loadActivityLogs();
    }
}

function applyFilters() {
    currentFilters = {
        username: document.getElementById('filterUsername').value.trim(),
        activity_type: document.getElementById('filterType').value
    };
    currentPage = 1;
    loadActivityLogs();
}

function clearFilters() {
    document.getElementById('filterUsername').value = '';
    document.getElementById('filterType').value = '';
    currentFilters = {};
    currentPage = 1;
    loadActivityLogs();
}

function refreshData() {
    loadStats();
    loadActivityLogs();
}

function handleAuthError() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    localStorage.removeItem(USER_ROLE_KEY);
    window.location.href = '/login.html';
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

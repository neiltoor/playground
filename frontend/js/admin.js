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
    loadLoginRequests();
    loadPendingCount();
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

// ===== Login Requests Management =====

// State for login requests
let currentRequestId = null;
let currentRequestEmail = null;
let currentRequestReason = null;

async function loadPendingCount() {
    try {
        const response = await fetch(`${API_BASE_URL}/login-requests/pending-count`, {
            headers: getAuthHeaders()
        });
        if (response.ok) {
            const data = await response.json();
            document.getElementById('pendingBadge').textContent = `${data.pending_count} pending`;
        }
    } catch (error) {
        console.error('Error loading pending count:', error);
    }
}

async function loadLoginRequests() {
    try {
        const status = document.getElementById('requestStatusFilter').value;
        let url = `${API_BASE_URL}/login-requests?limit=50`;
        if (status) url += `&status=${status}`;

        const response = await fetch(url, { headers: getAuthHeaders() });

        if (response.status === 401 || response.status === 403) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to load login requests');
        }

        const data = await response.json();
        renderLoginRequests(data.requests);
    } catch (error) {
        console.error('Error loading login requests:', error);
        document.getElementById('requestsTableBody').innerHTML =
            '<tr><td colspan="6" class="no-data">Error loading requests</td></tr>';
    }
}

function renderLoginRequests(requests) {
    const tbody = document.getElementById('requestsTableBody');

    if (requests.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="no-data">No requests found</td></tr>';
        return;
    }

    tbody.innerHTML = requests.map(req => `
        <tr>
            <td>${formatTimestamp(req.created_at)}</td>
            <td>${escapeHtml(req.email)}</td>
            <td class="reason-cell" title="${escapeHtml(req.reason || '')}">${escapeHtml(truncateText(req.reason || '-', 50))}</td>
            <td><span class="status-badge status-${req.status}">${req.status}</span></td>
            <td><code>${escapeHtml(req.request_ip || '-')}</code></td>
            <td class="actions-cell">
                ${req.status === 'pending' ? `
                    <button class="btn btn-sm btn-primary" onclick="openApprovalModal(${req.id}, '${escapeAttr(req.email)}', '${escapeAttr(req.reason || '')}')">Approve</button>
                    <button class="btn btn-sm btn-danger" onclick="rejectRequest(${req.id})">Reject</button>
                ` : `
                    <span class="reviewed-info">
                        ${req.assigned_username ? `<strong>${escapeHtml(req.assigned_username)}</strong>` : ''}
                        ${req.reviewed_by ? `<br><small>by ${escapeHtml(req.reviewed_by)}</small>` : ''}
                    </span>
                `}
            </td>
        </tr>
    `).join('');
}

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function escapeAttr(text) {
    if (!text) return '';
    return text.replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, ' ');
}

function openApprovalModal(requestId, email, reason) {
    currentRequestId = requestId;
    currentRequestEmail = email;
    currentRequestReason = reason;

    document.getElementById('approvalEmail').textContent = email;
    document.getElementById('approvalReason').textContent = reason || 'No reason provided';

    // Suggest username from email
    const suggestedUsername = email.split('@')[0].replace(/[^a-zA-Z0-9_]/g, '_').toLowerCase();
    document.getElementById('newUsername').value = suggestedUsername;
    document.getElementById('newPassword').value = '';
    document.getElementById('newRole').value = 'user';
    document.getElementById('approvalNotes').value = '';

    document.getElementById('approvalModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('approvalModal').style.display = 'none';
    currentRequestId = null;
    currentRequestEmail = null;
    currentRequestReason = null;
}

function generatePassword() {
    const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%';
    let password = '';
    for (let i = 0; i < 12; i++) {
        password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    document.getElementById('newPassword').value = password;
}

// Handle approval form submission
document.addEventListener('DOMContentLoaded', () => {
    const approvalForm = document.getElementById('approvalForm');
    if (approvalForm) {
        approvalForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('newUsername').value.trim();
            const password = document.getElementById('newPassword').value;
            const role = document.getElementById('newRole').value;
            const notes = document.getElementById('approvalNotes').value.trim();

            if (!username || !password) {
                alert('Please enter both username and password');
                return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/login-requests/${currentRequestId}/approve`, {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ username, password, role, notes })
                });

                if (!response.ok) {
                    const error = await response.json();
                    let errorMsg = 'Approval failed';
                    if (typeof error.detail === 'string') {
                        errorMsg = error.detail;
                    } else if (Array.isArray(error.detail)) {
                        errorMsg = error.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
                    }
                    throw new Error(errorMsg);
                }

                const data = await response.json();
                alert(`User '${data.username}' created successfully!\n\nPassword: ${password}\n\nMake sure to share these credentials securely.`);
                closeModal();
                loadLoginRequests();
                loadPendingCount();
            } catch (error) {
                alert('Error: ' + error.message);
            }
        });
    }
});

async function rejectRequest(requestId) {
    if (!confirm('Are you sure you want to reject this request?')) return;

    try {
        const response = await fetch(`${API_BASE_URL}/login-requests/${requestId}/reject`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ notes: 'Rejected by admin' })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Rejection failed');
        }

        loadLoginRequests();
        loadPendingCount();
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function refreshLoginRequests() {
    loadLoginRequests();
    loadPendingCount();
}

// Handle filter change
document.addEventListener('DOMContentLoaded', () => {
    const statusFilter = document.getElementById('requestStatusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', () => {
            loadLoginRequests();
        });
    }
});

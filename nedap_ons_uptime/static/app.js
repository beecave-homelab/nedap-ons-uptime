const API_BASE = '/api';

let currentTargetId = null;
let appTimezone = 'Europe/Amsterdam';
let targets = [];
let authState = {
    authEnabled: true,
    authenticated: false,
};

// Theme management
const theme = {
    get() {
        return localStorage.getItem('theme') || 'light';
    },
    set(mode) {
        localStorage.setItem('theme', mode);
        document.documentElement.setAttribute('data-theme', mode);
        this.updateToggleIcon(mode);
    },
    toggle() {
        const newMode = this.get() === 'light' ? 'dark' : 'light';
        this.set(newMode);
    },
    init() {
        const savedTheme = this.get();
        document.documentElement.setAttribute('data-theme', savedTheme);
        this.updateToggleIcon(savedTheme);
    },
    updateToggleIcon(mode) {
        const sunIcon = document.querySelector('.sun-icon');
        const moonIcon = document.querySelector('.moon-icon');
        const themeText = document.querySelector('.theme-text');
        
        if (mode === 'dark') {
            sunIcon?.classList.add('hidden');
            moonIcon?.classList.remove('hidden');
            if (themeText) themeText.textContent = 'Light Mode';
        } else {
            sunIcon?.classList.remove('hidden');
            moonIcon?.classList.add('hidden');
            if (themeText) themeText.textContent = 'Dark Mode';
        }
    }
};

function isReadOnlyMode() {
    return authState.authEnabled && !authState.authenticated;
}

function setAuthError(message = '') {
    const authError = document.getElementById('auth-error');
    if (!authError) return;

    if (!message) {
        authError.textContent = '';
        authError.classList.add('hidden');
        return;
    }

    authError.textContent = message;
    authError.classList.remove('hidden');
}

function updateUiForAuthState() {
    const addBtn = document.getElementById('add-btn');
    const authStatusText = document.getElementById('auth-status-text');
    const loginSection = document.getElementById('auth-login-section');
    const logoutSection = document.getElementById('auth-logout-section');

    if (authState.authEnabled) {
        if (authState.authenticated) {
            authStatusText.textContent = 'Signed in';
            loginSection.classList.add('hidden');
            logoutSection.classList.remove('hidden');
            addBtn?.classList.remove('hidden');
        } else {
            authStatusText.textContent = 'Read-only mode';
            loginSection.classList.remove('hidden');
            logoutSection.classList.add('hidden');
            addBtn?.classList.add('hidden');
        }
    } else {
        authStatusText.textContent = 'Authentication disabled';
        loginSection.classList.add('hidden');
        logoutSection.classList.add('hidden');
        addBtn?.classList.remove('hidden');
    }
}

async function loadAuthState() {
    try {
        const state = await fetchAPI('/auth/me');
        authState = {
            authEnabled: state.auth_enabled,
            authenticated: state.authenticated,
        };
    } catch (error) {
        console.error('Error loading auth state:', error);
        authState = {
            authEnabled: true,
            authenticated: false,
        };
    }

    updateUiForAuthState();
}

async function handleLogin(event) {
    event.preventDefault();
    setAuthError('');

    const formData = new FormData(event.target);
    const payload = {
        username: formData.get('username'),
        password: formData.get('password'),
    };

    try {
        const state = await fetchAPI('/auth/login', {
            method: 'POST',
            body: JSON.stringify(payload),
        });

        authState = {
            authEnabled: state.auth_enabled,
            authenticated: state.authenticated,
        };
        event.target.reset();
        updateUiForAuthState();
        loadTargets();
    } catch (error) {
        if (error.status === 401) {
            setAuthError('Invalid username or password');
            return;
        }
        setAuthError('Failed to sign in. Please try again.');
    }
}

async function handleLogout() {
    setAuthError('');
    try {
        const state = await fetchAPI('/auth/logout', { method: 'POST' });
        authState = {
            authEnabled: state.auth_enabled,
            authenticated: state.authenticated,
        };
        updateUiForAuthState();
        loadTargets();
    } catch (error) {
        console.error('Error during logout:', error);
    }
}

function handleUnauthorizedWriteAction() {
    authState.authEnabled = true;
    authState.authenticated = false;
    updateUiForAuthState();
    setAuthError('Please sign in to modify targets.');
}

// API helper
async function fetchAPI(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    });
    
    if (!response.ok) {
        let detail = `API error: ${response.status}`;
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            try {
                const payload = await response.json();
                if (payload?.detail) {
                    detail = payload.detail;
                }
            } catch (error) {
                console.debug('Could not parse error payload', error);
            }
        }

        const apiError = new Error(detail);
        apiError.status = response.status;
        throw apiError;
    }
    
    if (response.status === 204) {
        return null;
    }

    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
        return null;
    }

    return response.json();
}

// Formatting helpers
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString(undefined, { 
        timeZone: appTimezone,
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatLatency(ms) {
    if (ms === null || ms === undefined) return '-';
    return `${ms} ms`;
}

function formatHttpStatus(status) {
    if (status === null || status === undefined) return '-';
    return status;
}

function renderStatusBadge(up) {
    if (up === null || up === undefined) {
        return '<span class="status-badge unknown"><span class="status-dot"></span>Unknown</span>';
    }
    return up 
        ? '<span class="status-badge up"><span class="status-dot"></span>Up</span>' 
        : '<span class="status-badge down"><span class="status-dot"></span>Down</span>';
}

// Load app configuration
async function loadAppConfig() {
    try {
        const config = await fetchAPI('/config');
        if (config?.app_timezone) {
            appTimezone = config.app_timezone;
        }
    } catch (error) {
        console.error('Error loading app config:', error);
    }
}

// Load targets
async function loadTargets() {
    try {
        const status = await fetchAPI('/status');
        const list = document.getElementById('targets-list');
        targets = status;
        const readOnlyMode = isReadOnlyMode();

        if (status.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <circle cx="12" cy="12" r="10"/>
                            <path d="M12 16v-4M12 8h.01"/>
                        </svg>
                    </div>
                    <h3>No targets configured</h3>
                    <p>Add your first monitoring target to get started with uptime monitoring</p>
                </div>
            `;
            updateStats(0, 0, 0, 0);
            return;
        }

        let upCount = 0;
        let downCount = 0;
        let totalLatency = 0;
        let latencyCount = 0;

        list.innerHTML = status.map(item => {
            if (item.up === true) upCount++;
            if (item.up === false) downCount++;
            if (item.latency_ms !== null) {
                totalLatency += item.latency_ms;
                latencyCount++;
            }

            const actions = readOnlyMode
                ? '<span class="readonly-pill">Read-only</span>'
                : `
                        <button class="btn btn-secondary btn-sm" onclick="editTarget('${item.target_id}')">Edit</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteTarget('${item.target_id}')">Delete</button>
                    `;

            return `
                <div class="target-row">
                    <div class="target-name">
                        <a href="#" onclick="showDetails('${item.target_id}', '${item.name.replace(/'/g, "\\'")}'); return false;">${item.name}</a>
                    </div>
                    <div class="target-url" title="${item.url}">${item.url}</div>
                    <div class="target-status">${renderStatusBadge(item.up)}</div>
                    <div class="target-time">${formatDate(item.last_checked)}</div>
                    <div class="target-latency">${formatLatency(item.latency_ms)}</div>
                    <div class="target-http">${formatHttpStatus(item.http_status)}</div>
                    <div class="target-error" title="${item.error_message || ''}">${item.error_message || ''}</div>
                    <div class="target-actions">
                        ${actions}
                    </div>
                </div>
            `;
        }).join('');

        const avgLatency = latencyCount > 0 ? Math.round(totalLatency / latencyCount) : 0;
        updateStats(upCount, downCount, status.length, avgLatency);
        
        // Update history filter targets
        updateHistoryFilterTargets(status);
    } catch (error) {
        console.error('Error loading targets:', error);
    }
}

function updateStats(up, down, total, avg) {
    document.getElementById('stat-up').textContent = up;
    document.getElementById('stat-down').textContent = down;
    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-avg').textContent = avg > 0 ? `${avg}ms` : '0ms';
}

function updateHistoryFilterTargets(statusList) {
    const select = document.getElementById('history-filter-target');
    const currentValue = select.value;
    
    let options = '<option value="">All Targets</option>';
    statusList.forEach(item => {
        options += `<option value="${item.target_id}">${item.name}</option>`;
    });
    
    select.innerHTML = options;
    select.value = currentValue;
}

// Show target details
async function showDetails(targetId, name) {
    currentTargetId = targetId;
    document.getElementById('details-title').textContent = name;
    document.getElementById('details-panel').classList.remove('hidden');

    try {
        // Load uptime stats
        const uptime = await fetchAPI(`/targets/${targetId}/uptime?days=30`);
        document.getElementById('uptime-percentage').textContent = uptime.uptime_percentage.toFixed(1) + '%';
        document.getElementById('uptime-details').textContent = 
            `${uptime.up_checks} up, ${uptime.down_checks} down of ${uptime.total_checks} checks`;

        // Load recent history
        const history = await fetchAPI(`/targets/${targetId}/history?hours=24`);
        const historyContainer = document.getElementById('history-chart');
        
        if (history.length === 0) {
            historyContainer.innerHTML = '<p style="color: var(--text-muted); font-size: 14px;">No recent checks</p>';
        } else {
            historyContainer.innerHTML = history.slice(0, 20).map(check => `
                <div class="recent-item ${check.up ? 'up' : 'down'}">
                    <span class="recent-time">${formatDate(check.checked_at)}</span>
                    <span class="recent-status">${check.up ? 'UP' : 'DOWN'}</span>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading details:', error);
    }
}

// Load history
async function loadHistory() {
    const targetFilter = document.getElementById('history-filter-target').value;
    const statusFilter = document.getElementById('history-filter-status').value;
    const timeRange = document.getElementById('history-time-range').value;
    
    const list = document.getElementById('history-list');
    list.innerHTML = '<div class="history-loading">Loading history...</div>';
    
    try {
        // Build query params
        const params = new URLSearchParams();
        params.append('hours', timeRange);
        if (targetFilter) params.append('target_id', targetFilter);
        if (statusFilter) params.append('up', statusFilter);
        
        const history = await fetchAPI(`/history?${params.toString()}`);
        
        if (history.length === 0) {
            list.innerHTML = '<div class="history-empty">No history entries found for the selected filters</div>';
            return;
        }
        
        // Create a map of target IDs to names
        const targetMap = {};
        targets.forEach(t => {
            targetMap[t.target_id] = t.name;
        });
        
        list.innerHTML = history.map(check => `
            <div class="history-row">
                <div class="history-time">${formatDate(check.checked_at)}</div>
                <div class="history-target">${targetMap[check.target_id] || 'Unknown'}</div>
                <div class="target-status">${renderStatusBadge(check.up)}</div>
                <div class="history-latency">${formatLatency(check.latency_ms)}</div>
                <div class="history-http">${formatHttpStatus(check.http_status)}</div>
                <div class="history-error" title="${check.error_message || ''}">${check.error_message || ''}</div>
            </div>
        `).join('');
        
        // Load timeline for selected target
        if (targetFilter) {
            loadTimeline(targetFilter);
        } else {
            document.getElementById('uptime-timeline').innerHTML = 
                '<div class="timeline-loading">Select a specific target to view 30-day uptime history</div>';
        }
    } catch (error) {
        console.error('Error loading history:', error);
        list.innerHTML = '<div class="history-empty">Error loading history. Please try again.</div>';
    }
}

// Load daily uptime timeline
async function loadTimeline(targetId) {
    const timeline = document.getElementById('uptime-timeline');
    timeline.innerHTML = '<div class="timeline-loading">Loading timeline...</div>';
    
    try {
        const daily = await fetchAPI(`/targets/${targetId}/daily?days=30`);
        
        if (daily.length === 0) {
            timeline.innerHTML = '<div class="timeline-loading">No daily data available</div>';
            return;
        }
        
        // Calculate overall 30-day stats
        let totalChecks = 0;
        let totalUp = 0;
        daily.forEach(d => {
            totalChecks += d.total_checks;
            totalUp += d.up_checks;
        });
        const overallUptime = totalChecks > 0 ? (totalUp / totalChecks * 100).toFixed(2) : '100.00';
        
        // Get target name
        const target = targets.find(t => t.target_id === targetId);
        const targetName = target ? target.name : 'Target';
        
        // Update header with overall stats
        const header = document.querySelector('.timeline-header h3');
        if (header) {
            header.innerHTML = `${targetName} - 30 Day Uptime: <span style="color: var(--accent-success);">${overallUptime}%</span>`;
        }
        
        // Build timeline bars
        const barsHtml = daily.map(day => {
            let statusClass = 'no-data';
            let label = 'No Data';
            
            if (day.total_checks > 0) {
                if (day.uptime_percentage >= 99) {
                    statusClass = 'operational';
                    label = 'Operational';
                } else if (day.uptime_percentage >= 95) {
                    statusClass = 'degraded';
                    label = 'Degraded';
                } else {
                    statusClass = 'down';
                    label = 'Down';
                }
            }
            
            const date = new Date(day.date);
            const dateStr = date.toLocaleDateString(undefined, { 
                month: 'short', 
                day: 'numeric' 
            });
            
            const tooltip = day.total_checks > 0 
                ? `${dateStr}: ${day.uptime_percentage}% uptime (${day.up_checks}/${day.total_checks} checks)`
                : `${dateStr}: No data`;
            
            return `<div class="day-bar ${statusClass}" data-tooltip="${tooltip}"></div>`;
        }).join('');
        
        timeline.innerHTML = barsHtml;
        
        // Update date range labels
        if (daily.length > 0) {
            const startDate = new Date(daily[0].date);
            const endDate = new Date(daily[daily.length - 1].date);
            
            document.getElementById('timeline-start').textContent = startDate.toLocaleDateString(undefined, {
                month: 'short', day: 'numeric'
            });
            document.getElementById('timeline-end').textContent = endDate.toLocaleDateString(undefined, {
                month: 'short', day: 'numeric'
            });
        }
    } catch (error) {
        console.error('Error loading timeline:', error);
        timeline.innerHTML = '<div class="timeline-loading">Error loading timeline</div>';
    }
}

// Modal functions
function showModal(title) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal').classList.remove('hidden');
}

function hideModal() {
    document.getElementById('modal').classList.add('hidden');
    document.getElementById('target-form').reset();
    document.getElementById('target-id').value = '';
}

// Edit target
async function editTarget(targetId) {
    if (isReadOnlyMode()) {
        handleUnauthorizedWriteAction();
        return;
    }

    try {
        const target = await fetchAPI(`/targets/${targetId}`);
        document.getElementById('target-id').value = target.id;
        document.getElementById('name').value = target.name;
        document.getElementById('url').value = target.url;
        document.getElementById('interval_s').value = target.interval_s;
        document.getElementById('timeout_s').value = target.timeout_s;
        document.getElementById('enabled').checked = target.enabled;
        document.getElementById('verify_tls').checked = target.verify_tls;
        showModal('Edit Target');
    } catch (error) {
        console.error('Error loading target:', error);
    }
}

// Delete target
async function deleteTarget(targetId) {
    if (isReadOnlyMode()) {
        handleUnauthorizedWriteAction();
        return;
    }

    if (!confirm('Are you sure you want to delete this target?')) {
        return;
    }

    try {
        await fetchAPI(`/targets/${targetId}`, {
            method: 'DELETE',
        });
        loadTargets();
    } catch (error) {
        if (error.status === 401) {
            handleUnauthorizedWriteAction();
            return;
        }
        console.error('Error deleting target:', error);
        alert('Failed to delete target');
    }
}

// Tab switching
function switchTab(tabName) {
    // Update nav tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-tab`);
    });
    
    // Load history if switching to history tab
    if (tabName === 'history') {
        loadHistory();
    }
}

// Update system time
function updateSystemTime() {
    const now = new Date();
    document.getElementById('system-time').textContent = now.toLocaleTimeString(undefined, {
        timeZone: appTimezone,
        hour12: false
    });
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme
    theme.init();
    
    // Theme toggle
    document.getElementById('theme-toggle')?.addEventListener('click', () => {
        theme.toggle();
    });
    
    // Tab navigation
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            switchTab(tab.dataset.tab);
        });
    });
    
    // Add target button
    document.getElementById('add-btn')?.addEventListener('click', () => {
        if (isReadOnlyMode()) {
            handleUnauthorizedWriteAction();
            return;
        }
        showModal('Add Target');
    });

    document.getElementById('auth-login-form')?.addEventListener('submit', handleLogin);
    document.getElementById('logout-btn')?.addEventListener('click', handleLogout);
    
    // Cancel buttons
    document.getElementById('cancel-btn')?.addEventListener('click', hideModal);
    document.getElementById('cancel-btn-alt')?.addEventListener('click', hideModal);
    
    // Close details panel
    document.getElementById('close-details')?.addEventListener('click', () => {
        document.getElementById('details-panel').classList.add('hidden');
        currentTargetId = null;
    });
    
    // Modal overlay click
    document.getElementById('modal')?.addEventListener('click', (event) => {
        if (event.target.id === 'modal') {
            hideModal();
        }
    });
    
    // Escape key
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            hideModal();
            document.getElementById('details-panel').classList.add('hidden');
        }
    });
    
    // Form submit
    document.getElementById('target-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (isReadOnlyMode()) {
            handleUnauthorizedWriteAction();
            hideModal();
            return;
        }

        const formData = new FormData(e.target);
        const data = {
            name: formData.get('name'),
            url: formData.get('url'),
            interval_s: parseInt(formData.get('interval_s')),
            timeout_s: parseInt(formData.get('timeout_s')),
            enabled: formData.get('enabled') === 'on',
            verify_tls: formData.get('verify_tls') === 'on',
        };

        const targetId = document.getElementById('target-id').value;

        try {
            if (targetId) {
                await fetchAPI(`/targets/${targetId}`, {
                    method: 'PATCH',
                    body: JSON.stringify(data),
                });
            } else {
                await fetchAPI('/targets', {
                    method: 'POST',
                    body: JSON.stringify(data),
                });
            }
            hideModal();
            loadTargets();
        } catch (error) {
            if (error.status === 401) {
                handleUnauthorizedWriteAction();
                return;
            }
            console.error('Error saving target:', error);
            alert('Failed to save target');
        }
    });
    
    // History filters
    document.getElementById('history-filter-target')?.addEventListener('change', loadHistory);
    document.getElementById('history-filter-status')?.addEventListener('change', loadHistory);
    document.getElementById('history-time-range')?.addEventListener('change', loadHistory);
    
    // Initialize
    loadAppConfig().then(() => {
        loadAuthState().then(() => {
            loadTargets();
            updateSystemTime();
            setInterval(updateSystemTime, 1000);
            setInterval(loadTargets, 5000);
        });
    });
});

// Expose functions to global scope for inline onclick handlers
window.showDetails = showDetails;
window.editTarget = editTarget;
window.deleteTarget = deleteTarget;

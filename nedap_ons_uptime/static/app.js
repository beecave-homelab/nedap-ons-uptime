const API_BASE = '/api';

let currentTargetId = null;
let appTimezone = 'Europe/Amsterdam';

async function fetchAPI(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    });
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
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

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString(undefined, { timeZone: appTimezone });
}

async function loadAppConfig() {
    try {
        const config = await fetchAPI('/config');
        if (config?.app_timezone) {
            appTimezone = config.app_timezone;
        }
    } catch (error) {
        console.error('Error loading app config, using default timezone:', error);
    }
}

function renderStatus(status, up) {
    if (status === null || status === undefined) {
        return '<span class="status unknown">Unknown</span>';
    }
    return up 
        ? '<span class="status up">UP</span>' 
        : '<span class="status down">DOWN</span>';
}

async function loadTargets() {
    try {
        const status = await fetchAPI('/status');
        const tbody = document.getElementById('targets-body');

        if (status.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No targets configured yet. Use "Add Target" to start monitoring.</td></tr>';
            return;
        }

        tbody.innerHTML = status.map(item => `
            <tr>
                <td><a href="#" onclick="showDetails('${item.target_id}', '${item.name.replace(/'/g, "\\'")}'); return false;">${item.name}</a></td>
                <td>${item.url}</td>
                <td>${renderStatus(item.up, item.up)}</td>
                <td>${formatDate(item.last_checked)}</td>
                <td>${item.latency_ms !== null ? item.latency_ms + ' ms' : '-'}</td>
                <td>${item.http_status !== null ? item.http_status : '-'}</td>
                <td>${item.error_message ? `<span class="error">${item.error_message}</span>` : '-'}</td>
                <td class="actions">
                    <button class="btn small secondary" onclick="editTarget('${item.target_id}')">Edit</button>
                    <button class="btn small danger" onclick="deleteTarget('${item.target_id}')">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading targets:', error);
    }
}

async function showDetails(targetId, name) {
    currentTargetId = targetId;
    document.getElementById('details-title').textContent = name;
    document.getElementById('details-panel').classList.remove('hidden');

    try {
        const uptime = await fetchAPI(`/targets/${targetId}/uptime?days=30`);
        document.getElementById('uptime-percentage').textContent = uptime.uptime_percentage.toFixed(1) + '%';
        document.getElementById('uptime-details').textContent = 
            `${uptime.up_checks} up, ${uptime.down_checks} down of ${uptime.total_checks} checks`;

        const history = await fetchAPI(`/targets/${targetId}/history?hours=24`);
        const historyContainer = document.getElementById('history-chart');
        if (history.length === 0) {
            historyContainer.innerHTML = '<p>No history available</p>';
        } else {
            historyContainer.innerHTML = history.slice(0, 50).map(check => `
                <div class="history-item ${check.up ? 'up' : 'down'}">
                    <span>${formatDate(check.checked_at)}</span>
                    <span>${check.up ? 'UP' : 'DOWN'}</span>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading details:', error);
    }
}

document.getElementById('close-details').addEventListener('click', () => {
    document.getElementById('details-panel').classList.add('hidden');
    currentTargetId = null;
});

function showModal(title) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal').classList.remove('hidden');
}

function hideModal() {
    document.getElementById('modal').classList.add('hidden');
    document.getElementById('target-form').reset();
    document.getElementById('target-id').value = '';
}

document.getElementById('add-btn').addEventListener('click', () => {
    showModal('Add Target');
});

document.getElementById('cancel-btn').addEventListener('click', hideModal);

document.getElementById('modal').addEventListener('click', (event) => {
    if (event.target.id === 'modal') {
        hideModal();
    }
});

document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        hideModal();
    }
});

document.getElementById('target-form').addEventListener('submit', async (e) => {
    e.preventDefault();
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
        console.error('Error saving target:', error);
        alert('Failed to save target');
    }
});

async function editTarget(targetId) {
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

async function deleteTarget(targetId) {
    if (!confirm('Are you sure you want to delete this target?')) {
        return;
    }

    try {
        await fetchAPI(`/targets/${targetId}`, {
            method: 'DELETE',
        });
        loadTargets();
    } catch (error) {
        console.error('Error deleting target:', error);
        alert('Failed to delete target');
    }
}

async function init() {
    await loadAppConfig();
    await loadTargets();
    setInterval(loadTargets, 5000);
}

init();

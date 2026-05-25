// CortexFlow Dashboard Application
const pages = {
    dashboard: renderDashboard,
    agents: renderAgents,
    jobs: renderJobs,
    tokens: renderTokens,
    settings: renderSettings,
};

function showPage(name) {
    document.querySelectorAll('.nav-links li').forEach(l => l.classList.remove('active'));
    document.querySelector(`.nav-links a[data-page="${name}"]`)?.parentElement.classList.add('active');
    document.getElementById('page-title').textContent =
        name.charAt(0).toUpperCase() + name.slice(1);
    pages[name]?.();
}

document.querySelectorAll('.nav-links a').forEach(a => {
    a.addEventListener('click', e => {
        e.preventDefault();
        showPage(a.dataset.page);
    });
});

document.getElementById('refreshBtn')?.addEventListener('click', () => {
    const active = document.querySelector('.nav-links li.active a');
    if (active) showPage(active.dataset.page);
});

async function renderDashboard() {
    const [health, tokens] = await Promise.all([
        apiGet('/health'),
        apiGet('/tokens'),
    ]);
    const container = document.getElementById('page-content');
    container.innerHTML = `
        <div class="grid">
            <div class="card stat">
                <div class="stat-value">${health.agents_loaded || 0}</div>
                <div class="stat-label">Active Agents</div>
            </div>
            <div class="card stat">
                <div class="stat-value">${health.pipelines?.length || 0}</div>
                <div class="stat-label">Pipelines</div>
            </div>
            <div class="card stat">
                <div class="stat-value">${((tokens?.total_all_time || 0) / 1000).toFixed(0)}K</div>
                <div class="stat-label">Total Tokens</div>
            </div>
            <div class="card stat">
                <div class="stat-value">${tokens?.monthly?.percent_used || 0}%</div>
                <div class="stat-label">Monthly Budget Used</div>
            </div>
        </div>
        <div class="card">
            <h3>Monthly Token Budget</h3>
            <div class="token-bar">
                <div class="token-fill" style="width:${tokens?.monthly?.percent_used || 0}%"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-top:8px;">
                <span>Used: ${((tokens?.monthly?.total || 0) / 1000000).toFixed(1)}M</span>
                <span>Budget: ${((tokens?.monthly?.budget || 0) / 1000000).toFixed(0)}M</span>
            </div>
        </div>
        <div class="card">
            <h3>Quick Actions</h3>
            <p style="color:var(--text-secondary);font-size:0.9rem;">
                Submit a code analysis job or explore agent capabilities.
            </p>
        </div>
    `;
}

async function renderAgents() {
    const data = await apiGet('/agents');
    const container = document.getElementById('page-content');
    const agents = data.agents || [];
    container.innerHTML = `
        <div class="agent-grid">
            ${agents.map(a => `
                <div class="agent-card">
                    <div class="agent-name">${a.name}</div>
                    <div class="agent-status">${a.info?.class || 'active'}</div>
                    <div style="margin-top:12px;font-size:0.85rem;color:var(--text-secondary);">
                        Version: ${a.info?.version || '1.0.0'}<br>
                        Calls: ${a.info?.total_calls || 0}
                    </div>
                </div>
            `).join('')}
        </div>
        <div style="margin-top:16px;color:var(--text-secondary);font-size:0.85rem;">
            Total: ${agents.length} agents loaded
        </div>
    `;
}

async function renderJobs() {
    const container = document.getElementById('page-content');
    container.innerHTML = `
        <div class="card">
            <h3>Recent Jobs</h3>
            <p style="color:var(--text-secondary);">Submit an analysis to see jobs here.</p>
        </div>
    `;
}

async function renderTokens() {
    const data = await apiGet('/tokens');
    const monthly = data.monthly || {};
    const byAgent = data.by_agent || {};
    const container = document.getElementById('page-content');
    container.innerHTML = `
        <div class="grid">
            <div class="card stat">
                <div class="stat-value">${(data.total_all_time / 1000000).toFixed(1)}M</div>
                <div class="stat-label">All Time Tokens</div>
            </div>
            <div class="card stat">
                <div class="stat-value">${data.total_api_calls || 0}</div>
                <div class="stat-label">API Calls</div>
            </div>
        </div>
        <div class="card">
            <h3>Monthly Usage</h3>
            ${Object.entries(monthly).map(([k,v]) => `
                <div class="metric-row">
                    <span class="metric-label">${k}</span>
                    <span class="metric-value">${typeof v === 'number' ? v.toLocaleString() : v}</span>
                </div>
            `).join('')}
        </div>
        <div class="card">
            <h3>Per-Agent Usage</h3>
            ${Object.entries(byAgent).map(([name, stats]) => `
                <div class="metric-row">
                    <span class="metric-label">${name}</span>
                    <span class="metric-value">${(stats.total / 1000).toFixed(0)}K tokens (${stats.calls} calls)</span>
                </div>
            `).join('')}
        </div>
    `;
}

function renderSettings() {
    const container = document.getElementById('page-content');
    container.innerHTML = `
        <div class="card">
            <h3>Platform Settings</h3>
            <div class="metric-row">
                <span class="metric-label">Max Concurrent Jobs</span>
                <span class="metric-value">10</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Monthly Budget</span>
                <span class="metric-value">50,000,000</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Alert Threshold</span>
                <span class="metric-value">1,000,000</span>
            </div>
        </div>
    `;
}

// Initial render
showPage('dashboard');

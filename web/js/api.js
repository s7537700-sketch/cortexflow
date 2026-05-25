// CortexFlow Dashboard API Client
const API_BASE = '/api/v1';

async function apiGet(path) {
    try {
        const res = await fetch(`${API_BASE}${path}`);
        return await res.json();
    } catch (err) {
        console.error(`API GET ${path}:`, err);
        return { error: err.message };
    }
}

async function apiPost(path, data) {
    try {
        const res = await fetch(`${API_BASE}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return await res.json();
    } catch (err) {
        console.error(`API POST ${path}:`, err);
        return { error: err.message };
    }
}

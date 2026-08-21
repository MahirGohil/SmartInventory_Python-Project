/**
 * csrf.js — Shared CSRF & Fetch Helper for Django
 */

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    // Fallback to meta tag if cookie is not directly accessible
    if (!cookieValue) {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            cookieValue = metaTag.getAttribute('content');
        }
    }
    return cookieValue;
}

function fetchJSON(url, options = {}) {
    const opts = { ...options };
    opts.headers = { ...opts.headers };

    const method = (opts.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
        const csrfToken = getCookie('csrftoken');
        if (csrfToken) {
            opts.headers['X-CSRFToken'] = csrfToken;
        }
    }

    if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(opts.body);
    }

    return fetch(url, opts).then(async (response) => {
        if (!response.ok) {
            let errorMsg = `HTTP Error ${response.status}: ${response.statusText}`;
            try {
                const errData = await response.json();
                if (errData && errData.error) {
                    errorMsg = errData.error;
                }
            } catch (e) {
                // Not JSON
            }
            throw new Error(errorMsg);
        }
        return response.json();
    });
}

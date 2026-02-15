/**
 * history.js - Manages the history of resolved links using chrome.storage.local.
 */

export async function addRecord({ originalUrl, resolvedUrl, quality, format, provider, score }) {
    const record = {
        originalUrl,
        resolvedUrl,
        quality,
        format,
        provider,
        score,
        timestamp: Date.now()
    };

    const { history = [] } = await chrome.storage.local.get('history');
    history.unshift(record);
    
    // Keep only last 100
    if (history.length > 100) history.pop();
    
    await chrome.storage.local.set({ history });
    return record;
}

export async function getHistory() {
    const { history = [] } = await chrome.storage.local.get('history');
    return history;
}

export async function clearHistory() {
    await chrome.storage.local.set({ history: [] });
}

/**
 * options.js - Handles extension settings.
 */

document.addEventListener('DOMContentLoaded', async () => {
    const speedFactor = document.getElementById('speed-factor');
    const speedVal = document.getElementById('speed-val');
    const blockAds = document.getElementById('block-ads');
    const saveBtn = document.getElementById('save-btn');
    const status = document.getElementById('status');
    const clearHistoryBtn = document.getElementById('clear-history');

    // Load current settings
    const settings = await chrome.storage.sync.get({
        speedFactor: 20,
        blockAds: true
    });

    speedFactor.value = settings.speedFactor;
    speedVal.textContent = settings.speedFactor;
    blockAds.checked = settings.blockAds;

    speedFactor.addEventListener('input', () => {
        speedVal.textContent = speedFactor.value;
    });

    saveBtn.addEventListener('click', async () => {
        await chrome.storage.sync.set({
            speedFactor: parseInt(speedFactor.value),
            blockAds: blockAds.checked
        });
        
        status.textContent = "Settings saved!";
        setTimeout(() => { status.textContent = ""; }, 2000);
    });

    clearHistoryBtn.addEventListener('click', async () => {
        if (confirm("Are you sure you want to clear your history?")) {
            await chrome.storage.local.set({ history: [] });
            alert("History cleared.");
        }
    });
});

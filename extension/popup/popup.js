/**
 * popup.js - UI logic for the extension popup.
 */

document.addEventListener('DOMContentLoaded', async () => {
    const resolveBtn = document.getElementById('resolve-btn');
    const logDiv = document.getElementById('log');
    const resultBox = document.getElementById('result-box');
    const finalLinkSpan = document.getElementById('final-link');
    const copyBtn = document.getElementById('copy-btn');

    function addLog(msg) {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
        logDiv.appendChild(entry);
        logDiv.scrollTop = logDiv.scrollHeight;
    }

    resolveBtn.addEventListener('click', async () => {
        const quality = document.getElementById('quality').value;
        const format = document.getElementById('format').value;
        
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab) return;

        addLog(`Analyzing ${tab.url.substring(0, 30)}...`);
        
        chrome.runtime.sendMessage({
            action: "START_RESOLUTION",
            url: tab.url,
            criteria: {
                quality,
                format,
                providers: ["utorrent", "drive.google", "mega"]
            }
        });
    });

    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(finalLinkSpan.textContent);
        addLog("Link copied to clipboard!");
    });

    // Listen for updates from Background Script
    chrome.runtime.onMessage.addListener((request) => {
        if (request.action === "LOG") {
            addLog(request.message);
        }
        if (request.action === "RESOLVED") {
            resultBox.style.display = "block";
            finalLinkSpan.textContent = request.url;
            addLog("SUCCESS: Link found!");
        }
    });

    // Load saved settings if any
    const settings = await chrome.storage.sync.get(['quality', 'format']);
    if (settings.quality) document.getElementById('quality').value = settings.quality;
    if (settings.format) document.getElementById('format').value = settings.format;
});

/**
 * service-worker.js - Central orchestrator for the Neo-Link-Resolver extension.
 */

import { SearchCriteria, PROVIDER_PRIORITY } from '../lib/config.js';
import { LinkMatcher } from '../lib/matcher.js';
import { addRecord } from '../lib/history.js';

let activeResolutions = new Map(); // tabId -> resolutionState

// 1. URL Router
function getSiteType(url) {
    if (url.includes('peliculasgd.net') || url.includes('peliculasgd.co')) return 'peliculasgd';
    if (url.includes('hackstore.mx')) return 'hackstore';
    return null;
}

// 2. Monitoring for download links in traffic
chrome.webRequest.onBeforeRequest.addListener(
    (details) => {
        const url = details.url;
        const tabId = details.tabId;
        
        if (activeResolutions.has(tabId)) {
            const state = activeResolutions.get(tabId);
            const downloadDomains = ["drive.google.com", "mega.nz", "mediafire.com", "1fichier.com"];
            
            if (downloadDomains.some(d => url.includes(d)) && (url.includes("/view") || url.includes("/file") || url.includes("mega.nz/file"))) {
                console.log("[NeoSW] Download link captured from traffic:", url);
                state.capturedLinks.push(url);
                
                // If we're searching for this, notify popup
                chrome.runtime.sendMessage({ action: "LOG", message: `Captured download link: ${url.substring(0, 50)}...` });
                chrome.runtime.sendMessage({ action: "RESOLVED", url: url });
                activeResolutions.delete(tabId); // Success!
            }
        }
    },
    { urls: ["<all_urls>"] }
);

// 3. Message handler from Popup
chrome.runtime.onMessage.addListener(async (request, sender, sendResponse) => {
    if (request.action === "START_RESOLUTION") {
        const { url, criteria } = request;
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        if (!tab) return;
        
        activeResolutions.set(tab.id, {
            url,
            criteria: new SearchCriteria(criteria),
            capturedLinks: [],
            step: 'init'
        });

        const site = getSiteType(url);
        if (site === 'peliculasgd') {
            resolvePeliculasGD(tab.id, url);
        } else if (site === 'hackstore') {
            resolveHackStore(tab.id, url);
        } else {
            chrome.runtime.sendMessage({ action: "LOG", message: "Unsupported site." });
        }
    }
});

// 4. PeliculasGD Sequence
async function resolvePeliculasGD(tabId, url) {
    chrome.runtime.sendMessage({ action: "LOG", message: "Starting PeliculasGD resolution..." });
    
    // Step 1: Extract Token
    try {
        await chrome.scripting.executeScript({
            target: { tabId },
            files: ['content-scripts/peliculasgd/extractor.js']
        });

        const [result] = await chrome.tabs.sendMessage(tabId, { action: "EXTRACT_TOKEN" });
        if (result && result.success) {
            chrome.runtime.sendMessage({ action: "LOG", message: "Shortener URL found via token." });
            startShortenerChain(tabId, result.url);
        } else {
            // Step 2: Click button if no token
            const [btnResult] = await chrome.tabs.sendMessage(tabId, { action: "FIND_BUTTON" });
            if (btnResult && btnResult.success) {
                chrome.runtime.sendMessage({ action: "LOG", message: "Clicking download button..." });
                // We'd click and watch for new tab here
                // Simplified for brevity in this initial implementation
            }
        }
    } catch (err) {
        console.error(err);
    }
}

// 5. HackStore Sequence
async function resolveHackStore(tabId, url) {
    chrome.runtime.sendMessage({ action: "LOG", message: "Starting HackStore resolution..." });
    
    try {
        await chrome.scripting.executeScript({
            target: { tabId },
            files: ['content-scripts/hackstore/extractor.js']
        });

        await chrome.tabs.sendMessage(tabId, { action: "CLOSE_SPLASH" });
        const [qResult] = await chrome.tabs.sendMessage(tabId, { action: "DETECT_QUALITIES" });
        chrome.runtime.sendMessage({ action: "LOG", message: `Detected: ${qResult.qualities.join(', ')}` });

        const [pResult] = await chrome.tabs.sendMessage(tabId, { action: "EXTRACT_PROVIDERS" });
        // Use Matcher here in the real version
        if (pResult.providers.length > 0) {
            chrome.runtime.sendMessage({ action: "LOG", message: `Found ${pResult.providers.length} providers.` });
        }
    } catch (err) {
        console.error(err);
    }
}

// 6. Shortener Chain logic
async function startShortenerChain(parentTabId, url) {
    chrome.runtime.sendMessage({ action: "LOG", message: `Opening shortener: ${url.substring(0, 40)}...` });
    
    // Create new tab for the shortener chain
    const newTab = await chrome.tabs.create({ url });
    const tabId = newTab.id;

    activeResolutions.set(tabId, {
        parentTabId,
        hops: 0,
        startTime: Date.now(),
        capturedLinks: []
    });

    // Listen for completion
    chrome.webNavigation.onCompleted.addListener(async function listener(details) {
        if (details.tabId === tabId && details.frameId === 0) {
            chrome.runtime.sendMessage({ action: "LOG", message: "Page loaded. Accelerating timers..." });
            
            // Inject timer accel (MAIN WORLD)
            try {
                await chrome.scripting.executeScript({
                    target: { tabId },
                    files: ['content-scripts/common/timer-accel.js'],
                    world: 'MAIN'
                });
                
                // Trigger acceleration
                await chrome.scripting.executeScript({
                    target: { tabId },
                    func: () => window.__neoAccelerate && window.__neoAccelerate(),
                    world: 'MAIN'
                });

                // Inject handler (ISOLATED WORLD)
                await chrome.scripting.executeScript({
                    target: { tabId },
                    files: ['content-scripts/shortener/handler.js']
                });

                // Find and click continue
                const [result] = await chrome.tabs.sendMessageUnchecked(tabId, { action: "FIND_CONTINUE" });
                if (result && result.success) {
                    chrome.runtime.sendMessage({ action: "LOG", message: "Continue button found and clicked." });
                }
            } catch (err) {
                console.error("Injection error:", err);
            }
        }
    });
}

// Helper to avoid uncaught errors on closed tabs
chrome.tabs.sendMessageUnchecked = function(tabId, message) {
    return new Promise((resolve) => {
        chrome.tabs.sendMessage(tabId, message, (response) => {
            if (chrome.runtime.lastError) resolve([null]);
            else resolve([response]);
        });
    });
};

console.log("[NeoSW] Service worker active.");

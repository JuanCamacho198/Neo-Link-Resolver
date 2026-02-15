/**
 * service-worker.js - Central orchestrator for the Neo-Link-Resolver extension.
 */

import { SearchCriteria, PROVIDER_PRIORITY } from '../lib/config.js';
import { LinkMatcher } from '../lib/matcher.js';
import { addRecord } from '../lib/history.js';

let activeResolutions = new Map(); // tabId -> resolutionState

// 0. Messaging Helpers
function notifyPopup(message) {
    chrome.runtime.sendMessage(message).catch(() => {
        // Silent catch: Popup probably closed
    });
}

async function isTabValid(tabId) {
    try {
        const tab = await chrome.tabs.get(tabId);
        return !!tab;
    } catch {
        return false;
    }
}

async function safeExecuteScript(target, options) {
    try {
        if (!(await isTabValid(target.tabId))) return null;
        return await chrome.scripting.executeScript({ target, ...options });
    } catch (err) {
        if (!err.message.includes("No tab with id")) {
            console.error("Safe injection error:", err);
        }
        return null;
    }
}

async function safeTabMessage(tabId, message, retries = 3) {
    for (let i = 0; i < retries; i++) {
        try {
            if (!(await isTabValid(tabId))) return null;
            return await chrome.tabs.sendMessage(tabId, message);
        } catch (e) {
            if (i === retries - 1) throw e;
            await new Promise(r => setTimeout(r, 100)); // Small delay
        }
    }
}

// Global cleanup
chrome.tabs.onRemoved.addListener((tabId) => {
    activeResolutions.delete(tabId);
});

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
                notifyPopup({ action: "LOG", message: `Captured download link: ${url.substring(0, 50)}...` });
                notifyPopup({ action: "RESOLVED", url: url });
                activeResolutions.delete(tabId); // Success!
            }
        }
    },
    { urls: ["<all_urls>"] }
);

// 3. Message handler from Popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "START_RESOLUTION") {
        (async () => {
            const { url, criteria } = request;
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            if (!tab) {
                sendResponse({ success: false, error: "No active tab" });
                return;
            }
            
            activeResolutions.set(tab.id, {
                url,
                criteria: new SearchCriteria(criteria),
                capturedLinks: [],
                step: 'init'
            });

            const site = getSiteType(url);
            
            // Notify popup immediately
            sendResponse({ success: true, site });

            if (site === 'peliculasgd') {
                resolvePeliculasGD(tab.id, url);
            } else if (site === 'hackstore') {
                resolveHackStore(tab.id, url);
            } else {
                notifyPopup({ action: "LOG", message: "Sitio no compatible o no detectado." });
            }
        })();
        return true; // Keep channel open for async response
    }
});

// 4. PeliculasGD Sequence
async function resolvePeliculasGD(tabId, url) {
    notifyPopup({ action: "LOG", message: "Starting PeliculasGD resolution..." });
    
    // Step 1: Extract Token
    try {
        await safeExecuteScript(
            { tabId },
            { files: ['content-scripts/peliculasgd/extractor.js'] }
        );

        const result = await safeTabMessage(tabId, { action: "EXTRACT_TOKEN" });
        if (result && result.success) {
            notifyPopup({ action: "LOG", message: "Shortener URL found via token." });
            startShortenerChain(tabId, result.url);
        } else {
            // Step 2: Click button if no token
            const btnResult = await safeTabMessage(tabId, { action: "FIND_BUTTON" });
            if (btnResult && btnResult.success) {
                notifyPopup({ action: "LOG", message: "Clicking download button..." });
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
    notifyPopup({ action: "LOG", message: "Starting HackStore resolution..." });
    
    try {
        await safeExecuteScript(
            { tabId },
            { files: ['content-scripts/hackstore/extractor.js'] }
        );

        await safeTabMessage(tabId, { action: "CLOSE_SPLASH" });
        const qResult = await safeTabMessage(tabId, { action: "DETECT_QUALITIES" });
        notifyPopup({ action: "LOG", message: `Detected: ${qResult.qualities.join(', ')}` });

        const pResult = await safeTabMessage(tabId, { action: "EXTRACT_PROVIDERS" });
        // Use Matcher here in the real version
        if (pResult.providers.length > 0) {
            notifyPopup({ action: "LOG", message: `Found ${pResult.providers.length} providers.` });
        }
    } catch (err) {
        console.error(err);
    }
}

// 6. Shortener Chain logic
async function startShortenerChain(parentTabId, url) {
    notifyPopup({ action: "LOG", message: `Abriendo acortador: ${url.substring(0, 40)}...` });
    
    // Create new tab for the shortener chain
    const newTab = await chrome.tabs.create({ url });
    const tabId = newTab.id;

    activeResolutions.set(tabId, {
        parentTabId,
        type: 'shortener',
        startTime: Date.now(),
        capturedLinks: []
    });
}

// Global Navigation Handler
chrome.webNavigation.onCompleted.addListener(async (details) => {
    if (details.frameId !== 0) return;
    
    const tabId = details.tabId;
    if (!activeResolutions.has(tabId)) return;
    
    const state = activeResolutions.get(tabId);
    if (state.type !== 'shortener') return;

    notifyPopup({ action: "LOG", message: "Página cargada. Aplicando aceleración..." });
    
    try {
        if (!(await isTabValid(tabId))) return;

        // Inject timer accel (MAIN WORLD)
        await safeExecuteScript(
            { tabId },
            { files: ['content-scripts/common/timer-accel.js'], world: 'MAIN' }
        );
        
        // Trigger acceleration
        await safeExecuteScript(
            { tabId },
            {
                func: () => {
                    if (window.__neoAccelerate) window.__neoAccelerate();
                },
                world: 'MAIN'
            }
        );

        // Inject handler (ISOLATED WORLD)
        await safeExecuteScript(
            { tabId },
            { files: ['content-scripts/shortener/handler.js'] }
        );

        // Find and click continue
        const result = await safeTabMessage(tabId, { action: "FIND_CONTINUE" });
        if (result && result.success) {
            notifyPopup({ action: "LOG", message: "Botón de continuación activado automáticamente." });
        }
    } catch (err) {
        if (!err.message.includes("No tab with id")) {
            console.error("Injection error:", err);
        }
    }
});

console.log("[NeoSW] Service worker active.");

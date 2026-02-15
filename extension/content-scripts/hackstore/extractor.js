/**
 * hackstore/extractor.js - Extractor for HackStore.
 */

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "CLOSE_SPLASH") {
        const btn = Array.from(document.querySelectorAll('button, a')).find(el => el.innerText.toLowerCase().includes('continuar'));
        if (btn) {
            btn.click();
            sendResponse({ success: true });
        } else {
            sendResponse({ success: false });
        }
    }

    if (request.action === "DETECT_QUALITIES") {
        const qualityRegex = /2160p|1080p|720p|480p|360p|bdrip|bluray|web-dl/i;
        const found = new Set();
        document.querySelectorAll('h1, h2, h3, h4, b, strong, .font-bold, span').forEach(el => {
            const match = el.innerText.match(qualityRegex);
            if (match) found.add(match[0].toLowerCase());
        });
        sendResponse({ success: true, qualities: Array.from(found) });
    }

    if (request.action === "EXTRACT_PROVIDERS") {
        const providers = [];
        const keywords = ['mega', 'mediafire', 'drive', 'utorrent', '1fichier', 'gofile'];
        
        document.querySelectorAll('a, button').forEach((el, index) => {
            const text = el.innerText.toLowerCase();
            const href = (el.getAttribute('href') || "").toLowerCase();
            
            for (const kw of keywords) {
                if (text.includes(kw) || href.includes(kw)) {
                    providers.push({
                        index,
                        provider: kw,
                        text: el.innerText.trim(),
                        href: el.getAttribute('href')
                    });
                    break;
                }
            }
        });
        sendResponse({ success: true, providers });
    }

    return true;
});

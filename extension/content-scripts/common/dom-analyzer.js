/**
 * dom-analyzer.js - Scores elements based on their "realness".
 * Runs in ISOLATED world.
 */

function scoreElement(el) {
    let score = 0.5; // Starting point
    const rect = el.getBoundingClientRect();
    const area = rect.width * rect.height;
    const style = window.getComputedStyle(el);
    const text = el.innerText.toLowerCase();
    const href = el.getAttribute('href') || "";
    const idClass = (el.id + el.className).toLowerCase();

    // 1. Size signals
    if (area > 120000) score -= 0.3; // Likely a banner
    if (area < 400 && area > 0) score -= 0.2; // Likely a pixel

    // 2. Position signals
    if (style.position === 'fixed' || style.position === 'absolute') {
        if (parseInt(style.zIndex) > 100) score -= 0.4; // Overlay
    }

    // 3. Keyword signals
    if (idClass.includes('ad') || idClass.includes('banner') || idClass.includes('fake')) {
        score -= 0.4;
    }
    if (text.includes('descargar') || text.includes('download') || text.includes('get link')) {
        score += 0.3;
    }

    // 4. Style signals
    if (parseFloat(style.opacity) < 0.2) score -= 0.5;
    if (style.cursor === 'pointer') score += 0.1;

    // 5. URL signals
    const downloadDomains = ['mega.nz', 'drive.google', 'mediafire', '1fichier', 'gofile'];
    if (downloadDomains.some(d => href.includes(d))) {
        score += 0.3;
    }

    return Math.max(0, Math.min(1, score));
}

// Listen for messages from the background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "QUERY_ELEMENTS") {
        const results = [];
        const elements = document.querySelectorAll('a, button, div[role="button"]');
        elements.forEach((el, index) => {
            const score = scoreElement(el);
            if (score > 0.6) {
                results.push({
                    index,
                    text: el.innerText.trim(),
                    href: el.getAttribute('href'),
                    score: score
                });
            }
        });
        sendResponse({ elements: results });
    }
    return true;
});

/**
 * shortener/handler.js - Handler for jumping through shorteners.
 */

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "FIND_CONTINUE") {
        const keywords = ['get link', 'continuar', 'ingresar', 'haz clic aquí', 'click here'];
        const selectors = ['#getLink', '.btn-success', '#btn-main', '.download-link'];
        
        let found = null;

        // Search by text
        const allElements = Array.from(document.querySelectorAll('a, button'));
        for (const el of allElements) {
            const text = el.innerText.toLowerCase();
            if (keywords.some(kw => text.includes(kw)) && el.offsetWidth > 0 && el.offsetHeight > 0) {
                found = { type: 'text', text: el.innerText };
                el.scrollIntoView();
                el.style.border = "5px solid red"; // Visual feedback for debugging
                el.click(); // Auto-click if found
                break;
            }
        }

        if (!found) {
            // Search by selector
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.offsetWidth > 0 && el.offsetHeight > 0) {
                    found = { type: 'selector', selector: sel };
                    el.click();
                    break;
                }
            }
        }

        sendResponse({ success: !!found, details: found });
    }

    return true;
});

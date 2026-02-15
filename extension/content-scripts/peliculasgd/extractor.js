/**
 * peliculasgd/extractor.js - Extractor for PeliculasGD.
 */

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    const html = document.body.innerHTML;

    if (request.action === "EXTRACT_TOKEN") {
        const tokenMatch = html.match(/(r\.php\?f=|l\.php\?o=)([a-zA-Z0-9+/=]+)/);
        if (tokenMatch) {
            sendResponse({ 
                success: true, 
                url: `https://neworldtravel.com/${tokenMatch[1]}${tokenMatch[2]}` 
            });
        } else {
            const acortameMatch = html.match(/acortame\.site\/([a-zA-Z0-9]+)/);
            if (acortameMatch) {
                sendResponse({ 
                    success: true, 
                    url: `https://acortame.site/${acortameMatch[1]}` 
                });
            } else {
                sendResponse({ success: false });
            }
        }
    }

    if (request.action === "FIND_BUTTON") {
        const selectors = [
            "a:has(img[src*='cxx'])",
            "a:has-text('Enlaces Públicos')",
            "a:has-text('VER ENLACES')",
            "a:has-text('Descargar')",
            ".btn-download",
            "#download_link"
        ];
        
        // Note: :has-text is not valid CSS, we simulate it
        let found = null;
        const allLinks = Array.from(document.querySelectorAll('a, button'));
        
        for (const link of allLinks) {
            const text = link.innerText.toLowerCase();
            const hasImg = link.querySelector("img[src*='cxx']");
            
            if (hasImg || 
                text.includes('enlaces públicos') || 
                text.includes('ver enlaces') || 
                text.includes('descargar') ||
                link.classList.contains('btn-download') ||
                link.id === 'download_link') {
                
                found = {
                    href: link.getAttribute('href'),
                    tagName: link.tagName,
                    id: link.id,
                    className: link.className
                };
                break;
            }
        }
        sendResponse({ success: !!found, button: found });
    }

    return true;
});

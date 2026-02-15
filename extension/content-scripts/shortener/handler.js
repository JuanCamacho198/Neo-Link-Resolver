/**
 * shortener/handler.js - Handler for jumping through shorteners.
 */

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "FIND_CONTINUE") {
        // Palabras clave más específicas y ordenadas por relevancia
        const keywords = ['ir al enlace', 'get link', 'continuar', 'ingresar', 'haz clic aquí', 'click here'];
        const selectors = ['#getLink', '#btn-main', '.btn-success', '.download-link', 'button.continuar'];
        
        let found = null;

        // 1. Priorizar selectores específicos del sitio
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.offsetWidth > 0 && el.offsetHeight > 0) {
                // Verificar que no sea un anuncio (un anuncio suele tener 'google' o 'ad' en sus clases/ids)
                const isAd = el.closest('[id*="ad"], [class*="ad"], [id*="google"]');
                if (!isAd) {
                    found = { type: 'selector', selector: sel };
                    break;
                }
            }
        }

        // 2. Buscar por texto si no se encontró por selector
        if (!found) {
            const allElements = Array.from(document.querySelectorAll('a, button'));
            for (const el of allElements) {
                const text = el.innerText.toLowerCase();
                if (keywords.some(kw => text.includes(kw)) && el.offsetWidth > 0 && el.offsetHeight > 0) {
                    const isAd = el.closest('[id*="ad"], [class*="ad"], [id*="google"]');
                    if (!isAd) {
                        found = { type: 'text', text: el.innerText };
                        break;
                    }
                }
            }
        }

        if (found) {
            // Re-localizar el elemento para clickear
            const el = (found.type === 'selector') ? document.querySelector(found.selector) : 
                       Array.from(document.querySelectorAll('a, button')).find(e => e.innerText === found.text);
            
            if (el) {
                // Verificar que no haya un contador activo todavía
                const hasCountdown = document.body.innerText.match(/\d+ (segundos|seconds|s\.\.\.)/i);
                if (hasCountdown) {
                    console.log("[NeoHandler] Countdown detected, waiting...");
                    sendResponse({ success: false, reason: "countdown_active" });
                    return;
                }

                el.scrollIntoView();
                el.style.border = "5px solid #00FF00"; 
                
                // Delay para evadir detecciones (1.5s - 2.5s)
                const finalDelay = 1500 + Math.random() * 1000;
                setTimeout(() => {
                    if (!el.disabled && !el.classList.contains('disabled')) {
                        console.log("[NeoHandler] Clicking:", found);
                        el.click();
                    }
                }, finalDelay);
            }
        }

        sendResponse({ success: !!found, details: found });
    }
    return true;
});

/**
 * timer-accel.js - Accelerates timers and skips countdowns.
 * Runs in the MAIN world to access window objects.
 */

(function() {
    const SPEED_FACTOR = 20.0;
    const originalSetTimeout = window.setTimeout;
    const originalSetInterval = window.setInterval;

    // 1. Wrap timers
    window.setTimeout = function(handler, timeout, ...args) {
        if (timeout > 2000) {
            timeout = timeout / SPEED_FACTOR;
        }
        return originalSetTimeout.call(window, handler, timeout, ...args);
    };

    window.setInterval = function(handler, timeout, ...args) {
        if (timeout > 2000) {
            timeout = timeout / SPEED_FACTOR;
        }
        return originalSetInterval.call(window, handler, timeout, ...args);
    };

    // 2. Anti-debugger override
    const originalConstructor = Function.prototype.constructor;
    Function.prototype.constructor = function(str) {
        if (str === 'debugger') return function() {};
        return originalConstructor.apply(this, arguments);
    };

    // 3. Acceleration function exposed to Service Worker
    window.__neoAccelerate = function() {
        console.log("[NeoTimer] Acceleration triggered manually");
        
        // PeliculasGD specific countdown manipulation
        if (window.counter !== undefined) window.counter = 1;
        if (window.seconds !== undefined) window.seconds = 1;
        if (window.timer !== undefined) window.timer = 1;

        const countdownElements = document.querySelectorAll('.timer, #counter, .countdown, #countdown');
        countdownElements.forEach(el => {
            if (el.innerText.match(/\d+/)) {
                el.innerText = "1";
            }
        });

        // Force enable buttons
        const buttons = document.querySelectorAll('button[disabled], a.disabled');
        buttons.forEach(btn => {
            btn.removeAttribute('disabled');
            btn.classList.remove('disabled');
            btn.style.pointerEvents = 'auto';
            btn.style.opacity = '1';
        });

        // Remove blocking overlays
        const overlays = document.querySelectorAll('div[style*="fixed"], div[style*="absolute"]');
        overlays.forEach(el => {
            const zIndex = window.getComputedStyle(el).zIndex;
            if (zIndex && parseInt(zIndex) > 100) {
                if (el.innerText.length < 50) { // Likely an ad overlay or blocker
                    el.style.display = 'none';
                }
            }
        });
    };

    console.log("[NeoTimer] Timer acceleration active");
})();

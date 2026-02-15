"""
timer_interceptor.py - Aceleración de timers (setTimeout/setInterval) vía JS Injection.
Útil para evitar esperas obligatorias de 30-60 segundos.
"""

from playwright.sync_api import Page
from logger import get_logger

class TimerInterceptor:
    """
    Inyecta scripts para acelerar el paso del tiempo en el navegador del cliente.
    """
    
    def __init__(self, speed_factor: float = 10.0):
        self.logger = get_logger()
        self.speed_factor = speed_factor

    def accelerate_timers(self, page: Page):
        """
        Inyecta un script que overridea setTimeout y setInterval.
        """
        self.logger.info(f"Injecting timer acceleration and anti-debugger (factor {self.speed_factor}x)...")
        
        # Script para acelerar timers
        acceleration_script = f"""
        (() => {{
            if (window._ACCELERATOR_READY) return;

            // Bloquear debugger
            if (typeof Function.prototype.constructor === 'function') {{
                const originalConstructor = Function.prototype.constructor;
                Function.prototype.constructor = function(str) {{
                    if (str === 'debugger') return function() {{}};
                    return originalConstructor.apply(this, arguments);
                }};
            }}
            
            window._ACCELERATOR = {{
                speed: {self.speed_factor},
                originalSetTimeout: window.setTimeout,
                originalSetInterval: window.setInterval
            }};

            window.setTimeout = function(callback, delay, ...args) {{
                if (delay > 2000) {{ // Solo acelerar timers > 2s
                    delay = delay / window._ACCELERATOR.speed;
                }}
                return window._ACCELERATOR.originalSetTimeout(callback, delay, ...args);
            }};

            window.setInterval = function(callback, delay, ...args) {{
                if (delay > 2000) {{
                    delay = delay / window._ACCELERATOR.speed;
                }}
                return window._ACCELERATOR.originalSetInterval(callback, delay, ...args);
            }};
            
            window._ACCELERATOR_READY = true;
            console.log("Timer acceleration active (Speed factor: " + window._ACCELERATOR.speed + ")");
        }})();
        """
        
        try:
            # Ejecutar inmediatamente y también en cada navegación futura
            page.add_init_script(acceleration_script)
            page.evaluate(acceleration_script)
        except Exception as e:
            self.logger.error(f"Failed to inject timer acceleration: {e}")

    def skip_peliculasgd_timer(self, page: Page):
        """
        Estrategia específica para peliculasgd que usa sistema de verificación temporal.
        
        INGENIERÍA INVERSA:
        - PeliculasGD usa una variable global 'window.seconds' o contador en el DOM
        - El botón se activa cuando el contador llega a 0
        - El script backend valida que el tiempo haya transcurrido (server-side check)
        
        ESTRATEGIA HÍBRIDA:
        1. Acelerar timers para reducir espera real
        2. Buscar y manipular contadores visuales
        3. Forzar activación de botones/links cuando sea posible
        4. NO intentar skipear completamente (puede causar bloqueos server-side)
        
        RESULTADO: Espera reducida de ~60s a ~12s sin alertar al servidor
        """
        self.logger.step("HACK", "Attempting to accelerate mandatory ad wait...")
        
        script = """
        (() => {
            // 1. Buscar variables comunes de contadores
            const originalSeconds = window.seconds || null;
            if (window.counter !== undefined) window.counter = Math.max(0, window.counter - 40);
            if (window.seconds !== undefined) window.seconds = Math.max(0, window.seconds - 40);
            if (window.timer !== undefined) window.timer = Math.max(0, window.timer - 40);
            
            // 2. Buscar elementos del DOM que parecen contadores y reducirlos
            const timerEls = document.querySelectorAll('.timer, #timer, #counter, .countdown, [id*="time"], [class*="time"]');
            timerEls.forEach(el => {
                if (!el || typeof el.innerText !== 'string') return;
                const match = el.innerText.match(/(\\d+)/);
                if (match) {
                    const currentValue = parseInt(match[1]);
                    if (currentValue > 10) {
                        const newValue = Math.max(10, currentValue - 40);
                        el.innerText = el.innerText.replace(/\\d+/, newValue.toString());
                        console.log("Timer element reduced:", currentValue, "->", newValue);
                    }
                }
            });
            
            // 3. Buscar botones deshabilitados y verificar si pueden activarse
            const disabledButtons = document.querySelectorAll('button[disabled], a.disabled, .btn-disabled');
            disabledButtons.forEach(btn => {
                const text = btn.innerText.toLowerCase();
                if (text.includes('continuar') || text.includes('descargar') || text.includes('siguiente')) {
                    // NO activar aún - solo loggear para monitoreo
                    console.log("Found disabled button (will auto-activate with timer):", text);
                }
            });
            
            // 4. Específico de peliculasgd: Buscar función de validación
            if (typeof verifyHuman === 'function') {
                console.log("Found verifyHuman function - but NOT triggering (server-side validation)");
            }
            
            if (typeof enableDownload === 'function') {
                console.log("Found enableDownload function - monitoring...");
            }
            
            return {
                originalSeconds: originalSeconds,
                modified: true
            };
        })();
        """
        try:
            result = page.evaluate(script)
            if result and result.get('modified'):
                self.logger.info("Timer acceleration applied - wait time reduced significantly")
        except Exception as e:
            self.logger.info(f"PeliculasGD timer skip not applicable or failed: {e}")

    def force_enable_buttons(self, page: Page):
        """
        Intenta forzar la activación de botones deshabilitados después de un tiempo prudencial.
        Mejorado con múltiples selectores y estrategias de visibilidad.
        """
        self.logger.step("HACK", "Attempting to force-enable disabled buttons...")
        
        script = """
        (() => {
            let activated = 0;
            const selectors = [
                'button[disabled]', 'a.btn[disabled]', 'input[type="submit"][disabled]',
                '#getLink', '#btn-main', '.get-link', '.download-btn',
                'button.disabled', 'a.disabled', '.btn-disabled', '[aria-disabled="true"]'
            ];
            
            selectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    const text = el.innerText.toLowerCase();
                    const visible = !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                    
                    // 1. Eliminar overlays que podrían estar bloqueando el botón
                    const overlays = document.querySelectorAll('div[style*="position: fixed"], div[style*="z-index: 9991"], div[style*="z-index: 9992"], div[style*="z-index: 9993"], div[style*="z-index: 9994"], div[style*="z-index: 9995"], div[style*="z-index: 9996"], div[style*="z-index: 9997"], div[style*="z-index: 9998"], div[style*="z-index: 9999"], div[class*="overlay"], iframe:not([src*="google.com/recaptcha"])');
                    overlays.forEach(ov => {
                        const rect = ov.getBoundingClientRect();
                        // Si el overlay cubre gran parte de la pantalla o es transparente/fijo, lo removemos
                        if ((rect.width > window.innerWidth * 0.4 && rect.height > window.innerHeight * 0.4) || 
                            window.getComputedStyle(ov).position === 'fixed') {
                            ov.style.display = 'none';
                            ov.style.pointerEvents = 'none';
                            ov.remove();
                            console.log("Blocking overlay removed/disabled");
                        }
                    });

                    // 2. Solo activar botones relevantes o si el ID es muy específico
                    const goodKeywords = ['continuar', 'descargar', 'siguiente', 'get link', 'ir al enlace', 'ingresar', 'vínculo'];
                    if (goodKeywords.some(kw => text.includes(kw)) || 
                        el.id === 'getLink' || el.id === 'btn-main' || el.className.includes('btn-success')) {
                        
                        el.removeAttribute('disabled');
                        el.disabled = false;
                        el.classList.remove('disabled', 'btn-disabled');
                        
                        // Restaurar estilo y ponerlo al frente absoluto
                        el.style.setProperty('pointer-events', 'auto', 'important');
                        el.style.setProperty('opacity', '1', 'important');
                        el.style.setProperty('visibility', 'visible', 'important');
                        el.style.setProperty('display', 'block', 'important');
                        el.style.setProperty('zIndex', '2147483647', 'important'); // Max z-index
                        el.style.setProperty('position', 'relative', 'important');
                        
                        activated++;
                    }
                });
            });
            
            return { activated: activated };
        })();
        """
        
        try:
            result = page.evaluate(script)
            if result and result.get('activated', 0) > 0:
                self.logger.success(f"Force-enabled {result['activated']} button(s)")
            return result.get('activated', 0) > 0
        except Exception as e:
            self.logger.warning(f"Could not force-enable buttons: {e}")
            return False

    def detect_countdown(self, page: Page) -> bool:
        """Detecta si hay un countdown activo en la página."""
        script = """
        (() => {
            const texts = [
                document.body.innerText,
                ...Array.from(document.querySelectorAll('button, span, div')).map(el => el.innerText)
            ];
            // Buscar patrones como "Please wait 5 seconds", "Esperar 10s", etc.
            const regex = /(esper|wait|segundos|seconds|\\d+\\s*s)/i;
            return texts.some(t => regex.test(t) && /\\d+/.test(t));
        })()
        """
        try:
            return page.evaluate(script)
        except:
            return False

    def wait_and_click_when_ready(self, page: Page, timeout_ms: int = 20000) -> bool:
        """
        Espera a que un posible timer termine y clickea el botón resultante.
        Usa una estrategia combinada de esperar visibilidad y forzar activación.
        """
        self.logger.info(f"Waiting for button to be ready (timeout {timeout_ms}ms)...")
        
        start_time = __import__('time').time()
        selectors = [
            'a:has-text("Get Link")', 'button:has-text("Get Link")',
            'a:has-text("Continuar")', 'button:has-text("Continuar")',
            'a:has-text("Continue")', 'button:has-text("Continue")',
            'a:has-text("Ingresar")', 'button:has-text("Ingresar")',
            'a:has-text("Vínculo")', 'button:has-text("Vínculo")',
            'a:has-text("Ir al enlace")', 'button:has-text("Ir al enlace")',
            'div:has-text("Ingresar")', 'span:has-text("Ingresar")',
            '#getLink', '.btn-success', '.get-link', '#btn-main'
        ]
        
        while (__import__('time').time() - start_time) * 1000 < timeout_ms:
            for selector in selectors:
                try:
                    # Intentar encontrar un botón que sea visible y no deshabilitado
                    el = page.query_selector(selector)
                    if el and el.is_visible() and el.is_enabled():
                        self.logger.success(f"Button ready! Clicking {selector}...")
                        
                        # Triple estrategia de click:
                        # 1. Click JS nativo
                        # 2. Click Playwright (simula mouse)
                        # 3. dispatchEvent nativo
                        
                        try:
                            el.evaluate("node => { node.click(); node.dispatchEvent(new MouseEvent('click', {bubbles: true})); }")
                        except: pass
                        
                        try:
                            el.click(timeout=2000)
                        except: pass
                        
                        return True
                except:
                    continue
            
            # Si llevamos la mitad del tiempo, intentar forzar (solo una vez cada 5s)
            if (__import__('time').time() - start_time) * 1000 > timeout_ms / 2:
                if int(__import__('time').time()) % 5 == 0:
                    if self.force_enable_buttons(page):
                        page.wait_for_timeout(500)
                        continue
            
            page.wait_for_timeout(1000)
            
        self.logger.warning("Timed out waiting for button")
        return False

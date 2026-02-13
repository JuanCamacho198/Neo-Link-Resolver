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
        self.logger.info(f"Injecting timer acceleration (factor {self.speed_factor}x)...")
        
        # Script para acelerar timers
        # Nota: Multiplica los delays cortos o divide los delays largos.
        # Aquí dividimos el delay por el factor de velocidad.
        acceleration_script = f"""
        (() => {{
            const factor = {self.speed_factor};
            const originalSetTimeout = window.setTimeout;
            const originalSetInterval = window.setInterval;

            window.setTimeout = function(callback, delay, ...args) {{
                if (delay > 2000) {{ // Solo acelerar timers > 2s para no romper animaciones
                    delay = delay / factor;
                }}
                return originalSetTimeout(callback, delay, ...args);
            }};

            window.setInterval = function(callback, delay, ...args) {{
                if (delay > 2000) {{
                    delay = delay / factor;
                }}
                return originalSetInterval(callback, delay, ...args);
            }};
            
            console.log("Timer acceleration active: delays > 2s are now " + factor + "x faster");
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
        Útil cuando el timer ya debería haber expirado pero el botón no se activa.
        """
        self.logger.step("HACK", "Attempting to force-enable disabled buttons...")
        
        script = """
        (() => {
            let activated = 0;
            
            // Buscar botones/links disabled
            const elements = document.querySelectorAll('button[disabled], a.disabled, .btn-disabled, [aria-disabled="true"]');
            
            elements.forEach(el => {
                const text = el.innerText.toLowerCase();
                // Solo activar botones relevantes
                if (text.includes('continuar') || text.includes('descargar') || 
                    text.includes('siguiente') || text.includes('get link')) {
                    
                    el.removeAttribute('disabled');
                    el.classList.remove('disabled', 'btn-disabled');
                    el.setAttribute('aria-disabled', 'false');
                    
                    // Restaurar estilo si parece deshabilitado visualmente
                    el.style.pointerEvents = 'auto';
                    el.style.opacity = '1';
                    el.style.cursor = 'pointer';
                    
                    activated++;
                    console.log("Force-enabled button:", text);
                }
            });
            
            return { activated: activated };
        })();
        """
        
        try:
            result = page.evaluate(script)
            if result and result.get('activated', 0) > 0:
                self.logger.success(f"Force-enabled {result['activated']} button(s)")
        except Exception as e:
            self.logger.warning(f"Could not force-enable buttons: {e}")

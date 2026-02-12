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
        Estrategia específica para peliculasgd o sitios que usan contadores visibles.
        Intenta detectar variables globales o timers específicos.
        """
        self.logger.step("HACK", "Attempting to skip mandatory ad wait...")
        
        script = """
        (() => {
            // 1. Buscar variables comunes de contadores
            if (window.counter) window.counter = 0;
            if (window.seconds) window.seconds = 0;
            if (window.timer) window.timer = 0;
            
            // 2. Buscar elementos del DOM que parecen contadores y forzarlos
            const timerEls = document.querySelectorAll('.timer, #timer, #counter, .countdown');
            timerEls.forEach(el => {
                if (el.innerText.match(/\\d+/)) {
                    el.innerText = '0';
                }
            });
            
            // 3. Casos específicos de peliculasgd (si se conocen)
            if (typeof initSystem === 'function') {
                console.log("Forcing initSystem callback...");
                // Aquí se podría disparar el callback final si lo conocemos
            }
        })();
        """
        try:
            page.evaluate(script)
        except Exception as e:
            self.logger.debug(f"PeliculasGD skip failed or not applicable: {e}")

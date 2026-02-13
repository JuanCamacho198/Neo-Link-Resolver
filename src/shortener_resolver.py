"""
shortener_resolver.py - Resuelve cadenas de acortadores hasta llegar al link final.
Maneja timers, botones "Get Link" y redirecciones múltiples.
"""

import time
from typing import List, Optional, Dict
from playwright.sync_api import Page, Response, Error
from logger import get_logger
from network_analyzer import NetworkAnalyzer
from timer_interceptor import TimerInterceptor
from stealth_config import apply_stealth_to_page

class ShortenerChainResolver:
    """
    Sigue una cadena de acortadores automáticamente.
    Ejemplo: ouo.io -> acortame.site -> mega.nz
    """
    
    MAX_CHAIN_DEPTH = 8
    TIMER_WAIT_TIMEOUT = 30000  # 30s
    
    def __init__(self, network_analyzer: NetworkAnalyzer, timer_interceptor: TimerInterceptor):
        self.network = network_analyzer
        self.timer = timer_interceptor
        self.logger = get_logger()
        self.chain = []
        self.page = None

    def resolve(self, initial_url: str, page: Page) -> Optional[str]:
        """
        Punto de entrada principal. Intenta resolver la cadena hasta un link de descarga.
        """
        self.page = page
        self.logger.step("CHAIN", f"Starting chain resolution for: {initial_url[:50]}...")
        current_url = initial_url
        self.chain = []
        
        for depth in range(self.MAX_CHAIN_DEPTH):
            self.chain.append(current_url)
            self.logger.info(f"Chain step {depth + 1}/{self.MAX_CHAIN_DEPTH}: {current_url[:60]}")
            
            # 1. Ejecutar el paso (navegar y esperar)
            next_url = self._follow_step(current_url)
            
            if not next_url:
                self.logger.warning(f"Chain broke at step {depth + 1}")
                return None
            
            # 2. Si el siguiente es un link de descarga, ¡éxito!
            if self.network.is_download_url(next_url):
                self.logger.success(f"Final download link reached: {next_url[:80]}...")
                return next_url
            
            # 3. Si no es descarga pero es otro acortador, seguimos
            if self.network.is_shortener_url(next_url) or next_url != current_url:
                current_url = next_url
                continue
            
            # Si llegamos aquí y no es nada conocido, retornamos lo que tenemos
            self.logger.info("Reached unknown URL type, returning as candidate")
            return next_url
            
        self.logger.error(f"Max chain depth ({self.MAX_CHAIN_DEPTH}) reached")
        return None

    def _follow_step(self, url: str) -> Optional[str]:
        """Realiza un paso de navegación y detección."""
        try:
            # Si ya estamos en la URL (por redirect previo), no navegar de nuevo
            if self.page.url != url:
                self.logger.info(f"Navigating to {url[:60]}...")
                self.last_response = self.page.goto(url, wait_until="commit", timeout=45000)
            
            # Aplicar stealth y aceleración
            apply_stealth_to_page(self.page)
            self.timer.accelerate_timers(self.page)
            
            # Inyectar detector de redirecciones JS
            self._inject_redirect_interceptor()
            
            # Esperar a que la página cargue un poco
            self.page.wait_for_timeout(2000)
            
            # 1. Buscar en redirects 3xx capturados por network analyzer
            captured = self.network.get_best_link()
            if captured and captured not in self.chain:
                self.logger.info(f"Found next target in network traffic: {captured[:50]}")
                return captured

            # 2. Manejar timers y clicks si es necesario
            if self.timer.wait_and_click_when_ready(self.page, timeout_ms=self.TIMER_WAIT_TIMEOUT):
                self.page.wait_for_timeout(2000)
                # Verificar si el click causó una navegación o redirect
                new_url = self.page.url
                if new_url != url:
                    return new_url
            
            # 3. Buscar la "siguiente" URL en el DOM (redirecciones meta, assignments capturados)
            next_url = self._detect_next_url()
            if next_url:
                return next_url
            
            # Fallback: Revisar de nuevo el network analyzer por si el click disparó algo
            captured = self.network.get_best_link()
            if captured and captured not in self.chain:
                return captured
                
            return self.page.url # Retornar URL actual si nada cambió
            
        except Error as e:
            self.logger.error(f"Navigation error in chain: {e}")
            return None

    def _detect_next_url(self) -> Optional[str]:
        """Busca señales de la siguiente URL en la página actual."""
        # 1. Revisar si el interceptor JS capturó un window.location assignment
        captured_js = self.page.evaluate("window.__redirectTarget")
        if captured_js:
            self.logger.info(f"JS Interceptor captured redirect: {captured_js[:50]}")
            return captured_js
            
        # 2. Buscar tags <meta http-equiv="refresh">
        try:
            meta_refresh = self.page.evaluate("""() => {
                const meta = document.querySelector('meta[http-equiv="refresh"]');
                if (meta) {
                    const content = meta.getAttribute('content');
                    const match = content.match(/url=(.+)/i);
                    return match ? match[1] : null;
                }
                return null;
            }""")
            if meta_refresh:
                self.logger.info(f"Found meta-refresh redirect: {meta_refresh[:50]}")
                return meta_refresh
        except:
            pass
            
        # 3. Buscar links que parezcan ser de descarga final
        candidates = self.network.analyze_dom_links(self.page)
        if candidates:
            best = candidates[0]['url']
            if self.network.is_download_url(best):
                return best
                
        return None

    def _inject_redirect_interceptor(self):
        """Inyecta script para capturar redirecciones por JS."""
        script = """
        if (window.__redirectInterceptorInjected) return;
        window.__redirectInterceptorInjected = true;
        window.__redirectTarget = null;
        
        // Interceptar window.location = ...
        const originalLocation = window.location;
        // Nota: No podemos sobrescribir window.location directamente de forma fácil,
        // pero podemos atrapar cambios en href si se usa como setter.
        
        // Interceptar asignaciones a href, replace, assign
        const wrap = (obj, prop) => {
            const original = obj[prop];
            obj[prop] = function(url) {
                window.__redirectTarget = url;
                console.log("Captured JS redirect attempt via " + prop + ": " + url);
                return original.apply(this, arguments);
            };
        };
        
        // window.location.assign y replace son capturables
        try {
            const proto = Object.getPrototypeOf(window.location);
            const origAssign = window.location.assign;
            window.location.assign = function(url) {
                window.__redirectTarget = url;
                return origAssign.call(window.location, url);
            };
            const origReplace = window.location.replace;
            window.location.replace = function(url) {
                window.__redirectTarget = url;
                return origReplace.call(window.location, url);
            };
        } catch(e) {}
        """
        try:
            self.page.add_init_script(script)
            self.page.evaluate(script)
        except:
            pass

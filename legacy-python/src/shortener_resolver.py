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
        self.captured_redirects = []

    def resolve(self, initial_url: str, page: Page, referer: Optional[str] = None) -> Optional[str]:
        """
        Punto de entrada principal. Intenta resolver la cadena hasta un link de descarga.
        """
        self.page = page
        self.captured_redirects = []
        
        # Registrar listeners para capturar navegaciones y redirecciones HTTP
        def on_nav(frame):
            if frame == page.main_frame:
                url = frame.url
                if url and url not in self.captured_redirects and url != "about:blank":
                    self.captured_redirects.append(url)

        def on_response(response: Response):
            if 300 <= response.status < 400:
                loc = response.headers.get("location")
                if loc:
                    # Normalizar si es relativa
                    if loc.startswith('/'):
                        from urllib.parse import urljoin
                        loc = urljoin(response.url, loc)
                    if loc not in self.captured_redirects:
                        self.captured_redirects.append(loc)

        page.on("framenavigated", on_nav)
        page.on("response", on_response)

        try:
            self.logger.step("CHAIN", f"Starting chain resolution for: {initial_url[:50]}...")
            current_url = initial_url
            self.chain = []
            
            for depth in range(self.MAX_CHAIN_DEPTH):
                self.chain.append(current_url)
                self.logger.info(f"Chain step {depth + 1}/{self.MAX_CHAIN_DEPTH}: {current_url[:60]}")
                
                # 1. Ejecutar el paso (navegar y esperar)
                step_referer = referer if depth == 0 else None
                next_url = self._follow_step(current_url, referer=step_referer)
                
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
        finally:
            # Limpiar listeners
            try:
                page.remove_listener("framenavigated", on_nav)
                page.remove_listener("response", on_response)
            except: pass

    def _follow_step(self, url: str, referer: Optional[str] = None) -> Optional[str]:
        """Realiza un paso de navegación y detección."""
        try:
            # Si ya estamos en la URL (por redirect previo), no navegar de nuevo
            if self.page.url != url:
                self.logger.info(f"Navigating to {url[:60]}...")
                try:
                    self.page.goto(url, wait_until="commit", timeout=45000, referer=referer)
                except Error as e:
                    self.logger.debug(f"Navigation to {url[:30]} commit timeout (expected in redirects): {e}")
            
            # Aplicar aceleración de timers inmediatamente
            try:
                apply_stealth_to_page(self.page)
                self.timer.accelerate_timers(self.page)
            except Exception: pass
            
            # 1. Manejar timers y clicks específicos de PeliculasGD
            if "neworldtravel" in self.page.url or "acortame" in self.page.url:
                try:
                    # Forzar aceleración específica
                    self.timer.skip_peliculasgd_timer(self.page)
                except Exception as e:
                    self.logger.warning(f"Error applying specific timer skip: {e}")

            # 2. Esperar y hacer click en botones "Get Link"
            # Esperar un momento a que aparezcan los botones
            self.page.wait_for_timeout(2000)
            if self.timer.wait_and_click_when_ready(self.page, timeout_ms=self.TIMER_WAIT_TIMEOUT):
                # Esperar a que la navegación ocurra tras el click
                self.page.wait_for_timeout(2000)
            
            # 3. Detectar siguiente URL (Prioridad 1: Redirects capturados)
            next_url = self._detect_next_url()
            if next_url and next_url not in self.chain:
                return next_url
            
            # 4. Revisar si la navegación por click cambió el URL
            if self.page.url != url and self.page.url not in self.chain:
                return self.page.url
                
            return self.page.url # Retornar URL actual si nada cambió
            
        except Error as e:
            self.logger.error(f"Navigation error in chain: {e}")
            return None

    def _detect_next_url(self) -> Optional[str]:
        """Busca señales de la siguiente URL en la página actual o historial de navegación."""
        # 1. Revisar URLs capturadas por listeners (Navegación nativa)
        # Buscar la última URL capturada que no sea la actual y parezca legítima
        for url in reversed(self.captured_redirects):
            if url != self.page.url and url not in self.chain:
                # Priorizar si es descarga
                if self.network.is_download_url(url):
                    self.logger.info(f"Found download link in captured navigation: {url[:50]}")
                    return url
                # O si es acortador
                if self.network.is_shortener_url(url):
                    self.logger.info(f"Stepping into captured redirect: {url[:50]}")
                    return url
                    
        # 2. Buscar tags <meta http-equiv="refresh">
        try:
            meta_refresh = self.page.evaluate("""() => {
                const meta = document.querySelector('meta[http-equiv="refresh"]');
                if (meta) {
                    const content = meta.getAttribute('content');
                    const match = content.match(/url=(.+)/i);
                    return match ? match[1].replace(/['"]/g, '') : null;
                }
                return null;
            }""")
            if meta_refresh:
                if not meta_refresh.startswith('http'):
                    from urllib.parse import urljoin
                    meta_refresh = urljoin(self.page.url, meta_refresh)
                
                self.logger.info(f"Found meta-refresh redirect: {meta_refresh[:50]}")
                return meta_refresh
        except: pass
            
        # 3. Buscar links en el DOM
        candidates = self.network.analyze_dom_links(self.page)
        if candidates:
            # Filtrar candidatos que ya seguimos para evitar loops
            valid = [c for c in candidates if c['url'] not in self.chain]
            if valid:
                best = valid[0]['url']
                self.logger.info(f"Selected best link from DOM: {best[:50]}")
                return best
                
        return None
        try:
            self.page.add_init_script(script)
            self.page.evaluate(script)
        except:
            pass

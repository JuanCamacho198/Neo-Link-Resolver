import time
import random
import urllib.parse
from typing import List, Optional, Dict
from playwright.sync_api import Page, BrowserContext

from .base import SiteAdapter
from src.matcher import LinkOption
from src.url_parser import extract_metadata_from_url
from src.config import SearchCriteria

TIMEOUT_NAV = 40000

class PeliculasGDAdapter(SiteAdapter):
    """
    Adaptador ULTRA-ROBUSTO para PeliculasGD.net (7 pasos).
    Concepto: 'Scanner de Pestañas' + 'Network Sniffer'.
    No depende de una sola pestaña, sino que vigila todo el navegador.
    """
    
    def __init__(self, context: BrowserContext, criteria: SearchCriteria = None):
        super().__init__(context, criteria)
        self.final_link_found_in_network = None

    def can_handle(self, url: str) -> bool:
        return "peliculasgd.net" in url or "peliculasgd.co" in url

    def name(self) -> str:
        return "PeliculasGD"

    def resolve(self, url: str) -> LinkOption:
        page = self.context.new_page()
        
        # INYECTAR COOKIES DE SESIÓN SI LAS TENEMOS (Simular login/sesión válida)
        # Si el usuario nos da un valor de cookie, esto saltaría el check de VIP
        
        def on_response(response):
            try:
                r_url = response.url
                if "domk5.net" in r_url or ("drive.google.com" in r_url and "/view" in r_url):
                    if not self.final_link_found_in_network:
                        self.log("NETWORK", f"Final link detected: {r_url[:60]}...")
                        self.final_link_found_in_network = r_url
            except: pass
        self.context.on("response", on_response)

        try:
            self.log("INIT", f"Starting resolution for: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_NAV)
            
            # PASO 1: Enlaces Públicos
            self.log("STEP1", "Clicking 'Enlaces Públicos'...")
            # Detectar si nos han redirigido a la página de VIP
            if "miembros-vip" in page.url:
                self.log("ERROR", "Redirected to VIP members page. Site is enforcing bot protection or IP limit.")
                # INTENTO DE BYPASS: Volver atrás e intentar con un click más 'humano'
                page.go_back()
                time.sleep(2)

            target = page.wait_for_selector("a:has(img[src*='cxx']), a:has-text('Enlaces Públicos')", timeout=15000)
            
            # Movimiento humano antes del click para evitar detección
            target.hover()
            time.sleep(random.uniform(0.5, 1.2))
            target.click()
            time.sleep(5)
            
            # PASO 2/3: Extracción del link de redirección (EL PREMIO)
            # Buscamos en todas las pestañas el botón AQUI o similar
            redir_url = None
            for _ in range(10):
                for p in self.context.pages:
                    try:
                        if p.is_closed(): continue
                        # Buscar el link de Tulink directamente en el DOM
                        aqui = p.query_selector("a:has-text('AQUI'), a:has-text('Ingresa'), a[href*='tulink.org']")
                        if aqui:
                            redir_url = aqui.get_attribute("href")
                            if redir_url: break
                    except: continue
                if redir_url: break
                time.sleep(2)

            if not redir_url:
                raise Exception("No se pudo extraer el link de redirección (AQUI).")

            self.log("STEP3", f"Direct redirect link extracted: {redir_url[:50]}...")
            
            # PASO 4: Navegar al blog en una pestaña LIMPIA
            # Esto evita que los scripts de 'auto-close' de la página anterior nos maten
            blog_page = self.context.new_page()
            blog_page.goto(redir_url, referer="https://www.google.com/", timeout=TIMEOUT_NAV)
            
            # PASO 5-7: MARATHON
            self._marathon_watch(blog_page)
            
            if self.final_link_found_in_network:
                return self._create_result(self.final_link_found_in_network, url)
            
            raise Exception("No se pudo obtener el link final tras el maratón.")

        finally:
            self.context.on("response", on_response)

    def _marathon_watch(self, page: Page):
        """Vigila todas las pestañas abiertas buscando el link final."""
        self.log("MARATHON", "Watching tabs for the final link (up to 4 mins)...")
        start_time = time.time()
        
        scanner_script = """
            setInterval(() => {
                // Forzar timers de blog (WordPress/Blogspot timers comunes)
                const timerSelectors = ['#timer', '#contador', '.contador', '#count', '#countdown'];
                timerSelectors.forEach(sel => {
                    const el = document.querySelector(sel);
                    if (el && parseInt(el.innerText) > 1) {
                        el.innerText = '1'; // Forzar a casi terminar
                    }
                });
                if (typeof counter !== 'undefined') counter = 0;
                
                // Buscar links finales
                const allLinks = Array.from(document.querySelectorAll('a, button, [role="button"], iframe'));
                let found_href = null;

                for (const el of allLinks) {
                    const href = el.href || el.src || '';
                    const txt = (el.innerText || el.value || '').toUpperCase();
                    
                    if (href.includes('domk5.net') || (href.includes('drive.google.com') && (href.includes('/view') || href.includes('id=')))) {
                        found_href = href;
                        break;
                    }
                    
                    const matches = ['INGRESAR', 'VINCULO', 'ENLACE', 'CONTINUAR', 'PROSEGUIR', 'DESCARGAR', 'CLICK HERE', 'IR AL LINK'];
                    if (matches.some(m => txt.includes(m)) && !txt.includes('PRIVACIDAD')) {
                        // Si es un link de 'r.php' o similar, o un elemento interactivo (div/button)
                        if (href.includes('neworld') || href.includes('bit.ly') || !href || !href.includes(window.location.hostname)) {
                            el.style.border = '5px solid green';
                            el.click();
                        }
                    }
                }
                
                if (found_href) {
                    window.FINAL_LINK = found_href;
                }
            }, 1000);
        """

        while time.time() - start_time < 240:
            if self.final_link_found_in_network: return

            # Escanear cada página del contexto
            for p in self.context.pages:
                try:
                    if p.is_closed(): continue
                    url = p.url.lower()

                    # Si aterrizamos por navegación en el destino
                    if "domk5.net" in url or ("drive.google.com" in url and "/view" in url):
                        self.final_link_found_in_network = p.url
                        return

                    # "Despertador" para acortadores y blogs
                    is_shortener = "bit.ly" in url or "neworldtravel.com" in url or "safez.es" in url
                    is_blog = "saboresmexico" in url or "chef" in url or "receta" in url

                    if is_shortener or is_blog:
                        # Activar scanner en esta pestaña
                        try: p.evaluate(scanner_script)
                        except: pass
                        
                        # Consultar scanner
                        try:
                            found = p.evaluate("window.FINAL_LINK")
                            if found:
                                self.log("MARATHON", f"SUCCESS! Scanner found link: {found[:60]}...")
                                # Limpiar redirectores si es necesario
                                if "redir/?" in found: found = found.split("redir/?")[-1]
                                self.final_link_found_in_network = found
                                return
                        except: pass
                        
                        # Acción agresiva ocasional para despertar la página
                        elapsed_since_start = int(time.time() - start_time)
                        if elapsed_since_start % 15 == 0:
                            try:
                                self.log("DEBUG", f"Waking up page: {url[:30]}...")
                                p.bring_to_front()
                                # Movimiento errático y scroll
                                p.mouse.move(random.randint(200, 600), random.randint(200, 600))
                                p.mouse.wheel(0, 400)
                                time.sleep(0.5)
                                p.mouse.wheel(0, -200)
                                # Clic en el centro (a veces necesario para activar timers de 'humano')
                                p.mouse.click(400, 400)
                                p.keyboard.press("PageDown")
                            except: pass
                except: continue

            time.sleep(2)
            elapsed = int(time.time() - start_time)
            if elapsed % 20 == 0:
                urls = [p.url[:50] for p in self.context.pages if not p.is_closed()]
                self.log("MARATHON", f"Watching... {elapsed}s | Tabs: {len(urls)} | URLs: {urls}")

        # Si fallamos al final del loop
        if not self.final_link_found_in_network:
            self.log("MARATHON", "FAILED. Taking debug screenshots...")
            import os
            if not os.path.exists("screenshots"):
                os.makedirs("screenshots")
                
            for i, p in enumerate(self.context.pages):
                try:
                    if p.is_closed(): continue
                    url = p.url.lower()
                    name = "page"
                    if "neworldtravel" in url: name = "neworld"
                    elif "saboresmexico" in url: name = "blog"
                    elif "peliculasgd" in url: name = "main"
                    
                    filename = f"screenshots/debug_{name}_{i}.png"
                    p.screenshot(path=filename, full_page=False)
                    self.log("DEBUG", f"Saved screenshot: {filename} for {url[:50]}")
                except Exception as e:
                    self.log("DEBUG", f"Failed to take screenshot for page {i}: {str(e)}")

    def _click_and_wait(self, page: Page, element) -> Page:
        """Hace clic y retorna la nueva página si se abre una, si no retorna la actual."""
        try:
            # Esperar un poco para que los scripts carguen
            time.sleep(1)
            # Intentar clic vía JS para evitar que un popup bloquee el clic físico
            with self.context.expect_page(timeout=8000) as new_page_info:
                element.evaluate("el => el.click()")
            new_p = new_page_info.value
            new_p.wait_for_load_state("domcontentloaded", timeout=15000)
            return new_p
        except:
            # Si no hay nueva página, es que navegó en la misma pestaña o falló el popup
            return page

    def _create_result(self, final_url: str, original_url: str) -> LinkOption:
        meta = extract_metadata_from_url(original_url)
        return LinkOption(
            url=final_url,
            text=f"PeliculasGD - {meta.get('quality', '1080p')}",
            provider="GoogleDrive" if "drive.google" in final_url else "Direct",
            quality=meta.get('quality', "1080p"),
            format="MKV"
        )

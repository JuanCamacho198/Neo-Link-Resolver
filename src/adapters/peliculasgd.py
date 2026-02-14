import time
import random
import urllib.parse
from typing import List, Optional, Dict
from playwright.sync_api import Page, BrowserContext

from .base import SiteAdapter
try:
    from matcher import LinkOption
    from url_parser import extract_metadata_from_url
    from config import SearchCriteria
except ImportError:
    from ..matcher import LinkOption
    from ..url_parser import extract_metadata_from_url
    from ..config import SearchCriteria

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
            # Usar la misma página de PeliculasGD como referer para parecer más legítimo
            blog_page.goto(redir_url, referer=url, timeout=TIMEOUT_NAV)
            
            # PASO 5-7: MARATHON
            self._marathon_watch(blog_page)
            
            if self.final_link_found_in_network:
                return self._create_result(self.final_link_found_in_network, url)
            
            raise Exception("No se pudo obtener el link final tras el maratón.")

        finally:
            self.context.on("response", on_response)

    def _marathon_watch(self, page: Page):
        """Vigila todas las pestañas abiertas buscando el link final."""
        self.log("MARATHON", "Watching tabs (Simplified + Hidden Link Finder)...")
        start_time = time.time()
        self._nw_click_count = 0 
        
        scanner_script = """
            setInterval(() => {
                const url = window.location.href.toLowerCase();
                
                // 1. Quitar overlays que tapan el click (Estilo uBlock Lite)
                document.querySelectorAll('div, iframe, section, aside').forEach(el => {
                    try {
                        const style = window.getComputedStyle(el);
                        const z = parseInt(style.zIndex) || 0;
                        const pos = style.position;
                        
                        if (z > 500 || pos === 'fixed') {
                            // No borrar el contenedor del botón principal
                            if (el.querySelector('button#contador')) return;
                            
                            const rect = el.getBoundingClientRect();
                            if (rect.width > window.innerWidth * 0.4 && rect.height > window.innerHeight * 0.4) {
                                el.style.display = 'none'; // Mejor ocultar que borrar por si rompe layout
                                el.style.pointerEvents = 'none';
                            } else if (z > 1000) {
                                el.remove();
                            }
                        }
                    } catch(e) {}
                });

                // 2. Buscar SAFEZ en todo el HTML (incluso oculto)
                const bodyHtml = document.body.innerHTML;
                const safezMatch = bodyHtml.match(/https?:\/\/(www\.)?safez\.es\/[^"'\s<>]+/);
                if (safezMatch) {
                    window.FINAL_LINK = safezMatch[0];
                }

                // 3. Forzar botón NewWorld (MODO NATURAL)
                if (url.includes('neworldtravel.com')) {
                    const btn = document.querySelector('button#contador');
                    if (btn) {
                        const txt = btn.innerText.toUpperCase();
                        if (txt.includes('CONTINUAR') || txt.includes('ENLACE') || txt.includes('VINCULO')) {
                             if (!btn.disabled) {
                                 const oc = btn.getAttribute('onclick') || '';
                                 if (oc.includes('safez.es')) {
                                     const m = oc.match(/https?:\/\/safez\.es\/[^"']+/);
                                     if (m) window.FINAL_LINK = m[0];
                                 }
                             }
                        }
                    }
                }

                // 4. Búsqueda agresiva en variables y base64
                try {
                    const b64Potential = document.body.innerHTML.match(/[a-zA-Z0-9+\/]{30,}/g);
                    if (b64Potential) {
                        b64Potential.forEach(p => {
                            try {
                                const d = atob(p);
                                if (d.includes('safez.es')) {
                                    const m = d.match(/https?:\/\/safez\.es\/[^"'\s<>]+/);
                                    if (m) window.FINAL_LINK = m[0];
                                }
                            } catch(e){}
                        });
                    }
                } catch(e){}
            }, 1000);
        """

        while time.time() - start_time < 240:
            if self.final_link_found_in_network: return

            # Escanear cada página del contexto
            try:
                active_pages = [p for p in self.context.pages if not p.is_closed()]
            except:
                self.log("MARATHON", "Context closed or browser crashed. Stopping...")
                return
            
            # FOCUS LOCK: Prioridad absoluta a NewWorldTravel o Safez. Ignorar bit.ly intrusos.
            try:
                nw_page = next((p for p in active_pages if "neworldtravel.com" in p.url.lower()), None)
                safez_page = next((p for p in active_pages if "safez.es" in p.url.lower()), None)
                
                if safez_page:
                    safez_page.bring_to_front()
                elif nw_page:
                    nw_page.bring_to_front()
            except: pass

            for p in active_pages:
                try:
                    url = p.url.lower()

                    # Si aterrizamos por navegación en el destino o puente
                    if "domk5.net" in url or "safez.es" in url or ("drive.google.com" in url and "/view" in url) or "tulink.org/l.php" in url:
                        # Si es safez, a veces es solo un puente, seguimos vigilando pero lo reportamos
                        if "safez.es" in url:
                             self.log("MARATHON", f"Reached Link Protector: {url[:50]}")
                             # Si estamos en safez, el scanner debería encontrar el botón "Vincular"
                        elif "tulink.org" in url:
                             # Intentar forzar la carga si está trabada
                             try:
                                 if p.title() == "" or "Redirecting" in p.title():
                                     self.log("DEBUG", "Tulink bridge detected, forcing wait...")
                             except: pass
                        else:
                            self.final_link_found_in_network = p.url
                            return

                    # "Despertador" para acortadores y blogs
                    is_shortener = "bit.ly" in url or "neworldtravel.com" in url or "safez.es" in url or "tulink.org" in url
                    is_blog = "saboresmexico" in url or "chef" in url or "receta" in url

                    # Si hay NewWorldTravel y se abre un bit.ly, lo dejamos ahí pero NO le damos foco.
                    # El scanner correrá en él por si acaso tiene el link final.
                    
                    # Fase 5: Detección de bloqueo en NewWorldTravel
                    if "neworldtravel.com" in url or "google.com" in url:
                        # Si estamos en NewWorld, desactivar aceleración porque nos detectan
                        if "neworldtravel.com" in url:
                            try:
                                # NewWorldTravel detecta aceleración. Intentamos desactivarla si existe.
                                p.evaluate("if (window._ACCELERATOR) { window._ACCELERATOR.speed = 1.0; window._ACCELERATOR.active = false; }")
                            except: pass
                                
                        # CLICKER DE EMERGENCIA RAPIDO (SIMPLE)
                        if "neworldtravel.com" in url:
                            try:
                                if not hasattr(self, '_last_nw_click') or time.time() - self._last_nw_click > 8:
                                    btn = p.locator("button#contador").first
                                    if btn.is_visible() and not btn.is_disabled():
                                        txt = btn.inner_text().upper()
                                        
                                        # Solo clickear si el timer terminó de verdad (sin numeros en el texto)
                                        import re
                                        if ("CONTINUAR" in txt or "ENLACE" in txt) and not re.search(r'\d+', txt):
                                            self._nw_click_count += 1
                                            if self._nw_click_count > 15:
                                                self.log("ERROR", "NewWorld button clicked 15 times without success. Dump HTML...")
                                                try:
                                                    with open("logs/newworld_stuck.html", "w", encoding="utf-8") as f:
                                                        f.write(p.content())
                                                except: pass
                                                self.final_link_found_in_network = "FAILED:NEWWORLD_STUCK"
                                                return

                                            self.log("DEBUG", f"Ultra-human click NewWorld ({self._nw_click_count}/15): {txt}")
                                            
                                            # Traer al frente para asegurar que el click es registrado
                                            try: p.bring_to_front()
                                            except: pass
                                            time.sleep(0.5)

                                            # Intentar click por coordenadas con jitter
                                            try:
                                                box = btn.bounding_box()
                                                if box:
                                                    # Click un poco aleatorio dentro del botón
                                                    cx = box['x'] + box['width']*0.3 + random.uniform(0, box['width']*0.4)
                                                    cy = box['y'] + box['height']*0.3 + random.uniform(0, box['height']*0.4)
                                                    p.mouse.move(cx, cy, steps=5)
                                                    p.mouse.click(cx, cy, delay=random.uniform(100, 200))
                                                else:
                                                    btn.click(force=True, delay=200)
                                            except:
                                                btn.click(force=True, delay=200)
                                            
                                            # Si tras el click aparece un 'miembros-vip', lo cerramos
                                            self._last_nw_click = time.time()
                            except: pass

                        # Verificar si fue redirigido a Google o VIP (bloqueo de bot)
                        if ("google.com" in url and "search?" in url) or "miembros-vip" in url:
                            self.log("BLOCK", f"Redirección de bloqueo detectada ({url[:30]}). Cerrando pestaña...")
                            try:
                                if len(self.context.pages) > 1:
                                    p.close()
                                    continue
                            except: pass
                            continue

                    if is_shortener or is_blog:
                        # Activar scanner en esta pestaña y todos sus frames
                        for frame in p.frames:
                            try: frame.evaluate(scanner_script)
                            except: pass
                        
                        # Consultar scanner en todos los frames
                        for frame in p.frames:
                            try:
                                # Prioridad 1: Link final directo o puente Safez
                                found = frame.evaluate("window.FINAL_LINK")
                                if found:
                                    # Si es safez, seguimos vigilando para llegar al final, pero lo reportamos
                                    if "safez.es" in found:
                                        self.log("MARATHON", f"Bridge found: {found[:50]}... Navigating...")
                                        p.goto(found, wait_until="networkidle", timeout=30000)
                                        frame.evaluate("window.FINAL_LINK = null;")
                                        continue

                                    self.log("MARATHON", f"SUCCESS! Final link found: {found[:60]}...")
                                    self.final_link_found_in_network = found
                                    return
                                
                                # Prioridad 2: Link extraído de onclick (l.php?o=...)
                                onclick_url = frame.evaluate("window.EXTRACTED_ONCLICK")
                                if onclick_url and "l.php" in onclick_url:
                                    self.log("MARATHON", f"DIRECT BYPASS: Navigating to extracted onclick URL: {onclick_url[:60]}...")
                                    # Navegar directamente en lugar de clickear
                                    p.goto(onclick_url, wait_until="networkidle", timeout=30000)
                                    frame.evaluate("window.EXTRACTED_ONCLICK = null;") # Limpiar
                                    return # Si navegamos, salimos de este check para esperar el nuevo URL en el próximo loop
                            except: pass
                        
                            # Acción agresiva ocasional para despertar la página
                        elapsed_since_start = int(time.time() - start_time)
                        if elapsed_since_start % 10 == 0:
                            try:
                                # Movimientos suaves sin click automático (evita popups infinitos)
                                p.mouse.move(random.randint(100, 700), random.randint(100, 700), steps=5)
                                p.mouse.wheel(0, random.randint(200, 500))
                                time.sleep(0.3)
                                p.mouse.wheel(0, random.randint(-400, -100))
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

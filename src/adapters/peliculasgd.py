"""
adapters/peliculasgd.py - Adaptador para peliculasgd.net
Implementa el flujo completo de 7 pasos documentado en PLAN.md
"""

import re
import time
from typing import List, Dict, Optional
from playwright.sync_api import Page
from .base import SiteAdapter
from matcher import LinkOption
from config import TIMEOUT_NAV, TIMEOUT_ELEMENT, AD_WAIT_SECONDS
from human_sim import random_delay, simulate_human_behavior, human_mouse_move
from url_parser import extract_metadata_from_url


class PeliculasGDAdapter(SiteAdapter):
    """
    Adaptador para peliculasgd.net
    
    Implementa el flujo de 7 pasos para resolver el link final:
    Movie page -> Enlaces Publicos -> Intermediary 1 -> Intermediary 2 ->
    Google -> Human verification -> Ad click -> Final link
    """

    def can_handle(self, url: str) -> bool:
        return "peliculasgd.net" in url.lower()

    def name(self) -> str:
        return "PeliculasGD"

    def resolve(self, url: str) -> LinkOption:
        """
        Ejecuta el pipeline completo de navegacion y retorna el mejor link.
        """
        page = self.context.new_page()

        # Activar Network Interceptor si está disponible
        if self.network_analyzer:
            self.network_analyzer.setup_network_interception(page, block_ads=True)

        try:
            # Step 0: Abrir pagina de pelicula
            self.log("INIT", f"Opening {url[:60]}...")
            page.goto(url, timeout=TIMEOUT_NAV)
            page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
            
            # Step 1: Click "Enlaces Publicos"
            page_v1 = self._step1_click_enlaces_publicos(page)
            
            # Step 2: Haz clic aqui (en neworldtravel o similar)
            page_v2 = self._step2_click_haz_clic_aqui(page_v1)
            
            # Step 3: Google redirect / Boton Continuar
            page_v3 = self._step3_handle_redirect_chain(page_v2)
            
            # Step 4: Click primer resultado de Google
            verification_page = self._step4_click_first_google_result(page_v3)
            
            # Step 5 & 6: Verificación Humana + Ad Click + Timer (Proceso combinado)
            stage_page = self._step5_6_resolve_verification_and_timer(verification_page)
            
            # Step 7: Extraer link final
            final_link_data = self._step7_extract_final_link(stage_page)
            
            if not final_link_data:
                raise Exception("Failed to extract final link in step 7")

            # Metadatos para el resultado
            url_metadata = extract_metadata_from_url(url)
            
            return LinkOption(
                url=final_link_data["url"],
                text=f"PeliculasGD - {url_metadata.get('quality', '1080p')}",
                provider=self._detect_provider(final_link_data["url"]),
                quality=url_metadata.get('quality', ""),
                format=url_metadata.get('format', "")
            )

        except Exception as e:
            self.log("ERROR", f"Failed: {e}")
            page.screenshot(path="logs/peliculasgd_error_final.png")
            raise e
        finally:
            if not page.is_closed():
                page.close()

    # ---------------------------------------------------------------------------
    # Utilidades de Navegación
    # ---------------------------------------------------------------------------

    def _kill_cookies(self, page: Page):
        try:
            page.evaluate("""() => {
                const selectors = [
                    '.fc-consent-root', '.cc-window', '#onetrust-consent-sdk', 
                    '[id*="google-consent"]', '.asap-cookie-consent', 
                    '.cmplz-cookiebanner', '.cmplz-blocked-content-notice',
                    '#cmplz-cookiebanner-container', '.cmplz-soft-cookiewall',
                    '.cookie-notice-container', '#cookie-law-info-bar',
                    '.cmplz-overlay', '.cc-overlay'
                ];
                selectors.forEach(sel => {
                    const els = document.querySelectorAll(sel);
                    els.forEach(el => el.remove());
                });
                document.body.style.overflow = 'auto';
            }""")
        except: pass

    def _wait_for_new_page(self, page: Page, trigger_action, timeout=40_000) -> Page:
        initial_url = page.url
        for attempt in range(3):
            self.log("NAV", f"Interaction attempt {attempt + 1}...")
            
            # Limpiar overlays
            try:
                page.evaluate("() => { document.querySelectorAll('.fixed, [class*=\"overlay\"]').forEach(el => el.remove()); }")
            except: pass

            try:
                with self.context.expect_page(timeout=10000) as new_page_info:
                    trigger_action()
                new_p = new_page_info.value
                new_p.wait_for_load_state("domcontentloaded", timeout=15000)
                
                # Whitelist de dominios válidos para el flujo
                url = new_p.url.lower()
                valid_domains = ["google.com", "neworldtravel", "saboresmexico", "peliculasgd", "mediafire", "mega.nz", "drive.google"]
                
                if any(d in url for d in valid_domains):
                    self.log("NAV", f"New page valid: {url[:60]}")
                    return new_p
                else:
                    self.log("NAV", f"Closing ad popup: {url[:40]}")
                    new_p.close()
                    continue
            except:
                # Si no hay nueva página, ver si navegó en la misma
                page.wait_for_timeout(3000)
                if page.url != initial_url:
                    self.log("NAV", f"Same-tab navigation: {page.url[:60]}")
                    return page
        
        return page

    def log(self, step: str, msg: str):
        print(f"  [PeliculasGD:{step}] {msg}")

    # ---------------------------------------------------------------------------
    # Pasos del Flow
    # ---------------------------------------------------------------------------

    def _step1_click_enlaces_publicos(self, page: Page) -> Page:
        self.log("STEP1", "Looking for Enlaces Publicos link (image)...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        
        selectors = [
            "a:has(img[src*='cxx'])",
            "a:has(img.wp-image-125438)",
            "xpath=//strong[contains(text(), 'Enlaces Públicos')]/preceding-sibling::a[1]",
            "a:has-text('Enlaces Públicos')",
        ]
        
        target = None
        for sel in selectors:
            target = page.query_selector(sel)
            if target: break
            
        if not target:
            raise Exception("Enlaces Publicos link not found")
            
        return self._wait_for_new_page(page, lambda: target.click())

    def _step2_click_haz_clic_aqui(self, page: Page) -> Page:
        self.log("STEP2", "Looking for 'Haz clic aquí'...")
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        random_delay(2.0, 4.0)
        
        target = page.query_selector("text='Haz clic aquí'") or page.query_selector("a:has-text('Haz clic')")
        if not target:
            target = page.query_selector(".text:has-text('Haz clic')")
            
        if not target:
            raise Exception("'Haz clic aqui' button not found")
            
        return self._wait_for_new_page(page, lambda: target.click())

    def _step3_handle_redirect_chain(self, page: Page) -> Page:
        self.log("STEP3", "Handling redirect chain to Google...")
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        
        btn = page.query_selector("button.button-s") or page.query_selector("a.button-s")
        if btn:
            self.log("STEP3", "Clicking intermediate 'Continuar' button...")
            return self._wait_for_new_page(page, lambda: btn.click())
            
        start = time.time()
        while time.time() - start < 20:
            if "google.com/search" in page.url:
                return page
            page.wait_for_timeout(2000)
            
        return page

    def _step4_click_first_google_result(self, page: Page) -> Page:
        self.log("STEP4", "Clicking first Google result...")
        
        # 1. Esperar a que se quite el redirector href.li de forma agresiva
        start_wait = time.time()
        while time.time() - start_wait < 10:
            if "google.com" in page.url: break
            page.wait_for_timeout(500)

        # 2. Aceptación rápida de cookies/consentimiento
        try:
            page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                const accept = btns.find(b => /(Aceptar|Accept|Agree|Agree all|Aceptar todo)/i.test(b.innerText));
                if (accept) accept.click();
            }""")
        except: pass

        # 3. Búsqueda ultra-rápida del primer resultado genuino de saboresmexico
        combined_selector = "#search a h3, a h3, #rso a[href*='saboresmexico.com'] h3, .g a h3"
        
        self.log("STEP4", "Waiting for search results...")
        start_find = time.time()
        while time.time() - start_find < 20:
            try:
                # Usar evaluate para encontrar el primer link de saboresmexico que sea un resultado de búsqueda
                # Esto es más rápido que query_selector múltiple
                target_href = page.evaluate("""() => {
                    const links = Array.from(document.querySelectorAll('#search a, #rso a, .g a'));
                    const result = links.find(a => a.href.includes('saboresmexico.com') && (a.querySelector('h3') || a.innerText.length > 20));
                    if (result) {
                        result.scrollIntoView();
                        return result.href;
                    }
                    return null;
                }""")
                
                if target_href:
                    self.log("STEP4", f"Found result: {target_href[:40]}...")
                    # Clicar usando el selector que encontramos
                    el = page.query_selector(f"a[href='{target_href}']") or page.query_selector(f"a[href*='saboresmexico.com']")
                    if el:
                        # No esperamos a que la nueva página cargue totalmente aquí, 
                        # devolvemos el control rápido para que empiece el check de humano
                        return self._wait_for_new_page(page, lambda: el.click(force=True))
            except: pass
            
            if "google.com/sorry" in page.url:
                self.log("WARNING", "Google CAPTCHA! Try to solve it manually or waiting...")
                page.wait_for_timeout(2000)
            else:
                page.wait_for_timeout(500) # Poll cada 0.5s en lugar de 2s
        
        # Fallback de búsqueda directa si Google falla
        try:
            import urllib.parse
            q = urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query).get('q', [''])[0]
            clean_q = q.replace('site:saboresmexico.com', '').strip()
            if clean_q:
                self.log("STEP4", f"Google issue. Fallback search on site for: {clean_q}")
                page.goto(f"https://saboresmexico.com/?s={urllib.parse.quote(clean_q)}")
                first = page.wait_for_selector("article a, .entry-title a", timeout=10000)
                if first: return self._wait_for_new_page(page, lambda: first.click())
        except: pass

        raise Exception("Google search results not found or blocked")

    def _step5_6_resolve_verification_and_timer(self, page: Page) -> Page:
        self.log("STEP5/6", "Resolving blog verification (timer + article interaction)...")
        
        start_time = time.time()
        article_clicked = False
        
        while time.time() - start_time < 220:
            # 1. Buscar el botón en todas las páginas abiertas de saboresmexico
            pages = self.context.pages
            for p in pages:
                try:
                    if p.is_closed(): continue
                    url = p.url
                    if "saboresmexico" not in url: continue
                    
                    self.log("DEBUG", f"Scanning: {url[:40]} | Frames: {len(p.frames)}")
                    
                    # Detección de raíz mejorada
                    parsed_url = urllib.parse.urlparse(url)
                    is_root = len(parsed_url.path.strip("/")) == 0
                    
                    self._kill_cookies(p)
                    for frame in p.frames:
                        # Escaneo AGRESIVO: intentar obtener todos los elementos con texto sospechoso
                        try:
                            links = frame.evaluate("""() => {
                                // Buscar en TODO el documento
                                const all = Array.from(document.querySelectorAll('a, button, [role="button"], div, span, center'));
                                return all
                                    .filter(el => {
                                        const txt = (el.innerText || "").toLowerCase();
                                        return txt.includes("continuar") || txt.includes("link") || txt.includes("vínculo");
                                    })
                                    .map(el => ({
                                        text: el.innerText,
                                        tag: el.tagName,
                                        href: el.getAttribute('href') || el.getAttribute('data-href'),
                                        visible: el.offsetParent !== null,
                                        opacity: window.getComputedStyle(el).opacity
                                    }));
                            }""")
                            
                            if len(links) > 0:
                                self.log("DEBUG", f"Page {url[:20]} has {len(links)} text-matching elements")
                            
                            for l in links:
                                text = (l['text'] or "").lower()
                                href = (l['href'] or "").lower()
                                op = float(l['opacity'] or 0)
                                if not l['visible'] or op < 0.2: continue

                                self.log("DEBUG", f"Found candidate: '{text[:20]}' tag:{l['tag']} href:{href[:10]}")
                                
                                if "google.com" in href or "href.li" in href: continue

                                if "ingresa" in text or "vínculo" in text:
                                     self.log("STEP5/6", f"Found final button: {text}")
                                     return p
                                
                                if "continuar" in text or "get link" in text:
                                     if (time.time() - start_time) > 15:
                                         if not is_root or len(url) > 35:
                                             self.log("STEP5/6", f"Success: Clickable Continuar found in {url[:30]}")
                                             return p
                        except: continue
                except: continue

            # 2. Simulación humana y clic en artículo (solo si no se ha hecho)
            try:
                # Buscar una página de saboresmexico que esté abierta
                current_p = None
                for p in self.context.pages:
                    if not p.is_closed() and "saboresmexico.com" in p.url:
                        current_p = p
                        break
                
                if current_p:
                    self._kill_cookies(current_p)
                    if not article_clicked and (time.time() - start_time) > 4:
                        article = current_p.query_selector("aside a, .sidebar a, .recent-posts a")
                        if article:
                            self.log("STEP5/6", f"Clicking article to trigger timer: {article.get_attribute('href')}")
                            article_clicked = True
                            article.click(force=True)
                    
                    # Simulación humana constante
                    if random.random() > 0.5:
                        current_p.mouse.move(random.randint(100, 700), random.randint(100, 700))
                        current_p.mouse.wheel(0, 300)
                        time.sleep(0.1)
                        current_p.mouse.wheel(0, -200)
            except: pass

            time.sleep(5)
            # FOTO DE DEPURACION
            if int(time.time() - start_time) % 40 == 0:
                for p in self.context.pages:
                    if not p.is_closed() and "saboresmexico" in p.url:
                        p.screenshot(path=f"logs/debug_sabores_{int(time.time())}.png")

            self.log("STEP5/6", f"Waiting for timer... ({int(time.time() - start_time)}s)")
        
        raise Exception("Timeout waiting for blog verification button")

    def _step7_extract_final_link(self, page: Page) -> Optional[Dict]:
        self.log("STEP7", "Extracting final link (checking all tabs)...")
        
        # El usuario dice que hay que esperar y que la PRIMERA página que se abrió cambia su estado
        # Vamos a escanear todas las páginas abiertas periódicamente
        start_time = time.time()
        while time.time() - start_time < 120: # 120s para el paso final considerando el timer de 40s
            
            # Revisar todas las pestañas abiertas
            for p in self.context.pages:
                try:
                    if p.is_closed(): continue
                    url = p.url.lower()
                    
                    # 1. Si ya estamos directamente en un link de descarga
                    if any(x in url for x in ["drive.google.com", "mega.nz", "mediafire.com", "1fichier.com", "googledrive.com"]):
                        self.log("STEP7", f"Found final link in tab URL: {url[:60]}")
                        return {"url": p.url}

                    # Log periódico de escaneo
                    if elapsed % 20 == 0:
                        self.log("STEP7", f"Scanning tab: {url[:50]}")
                        # Hacer simulación humana en tabs de saboresmexico para despertar el timer
                        if "saboresmexico" in url:
                            try:
                                p.bring_to_front() # Muy importante para que el script de la web detecte al humano
                                p.mouse.move(300, 300)
                                p.mouse.wheel(0, 500)
                                p.wait_for_timeout(1000)
                                p.mouse.click(500, 500) # Clic neutral pedido por usuario
                                p.mouse.wheel(0, -300)
                                self._kill_cookies(p)
                            except: pass

                    # 2. Matar cookies en todas para ver botones
                    self._kill_cookies(p)

                    # 3. Buscar botones en esta página (incluyendo todos los frames)
                    for frame in p.frames:
                        try:
                            # Ignorar botones que sabemos que son circulares o basura
                            if "google.com" in url or "href.li" in url: continue
                            
                            # Selectores prioritarios según el usuario
                            selectors = [
                                "a:has-text('Ingresa al link')", # Prioridad 1
                                "a:has-text('Obtener Vínculo')", 
                                "button:has-text('Obtener Vínculo')",
                                "a:has-text('Continuar')", 
                                "button:has-text('Continuar')",
                                "a:has-text('Descargar Aqui')", 
                                "a:has-text('Ir al enlace')",
                                "#generar_link",
                                "center a"
                            ]
                            for sel in selectors:
                                try:
                                    btn = frame.query_selector(sel)
                                    if btn and btn.is_visible():
                                        inner_text = (btn.inner_text() or "").lower()
                                        opacity = btn.evaluate("el => getComputedStyle(el).opacity")
                                        href = btn.get_attribute("href") or ""
                                        
                                        # Si el botón abre Google o algo que no es descarga, ignorarlo en este escaneo
                                        if "google.com" in href or "href.li" in href or "facebook.com" in href:
                                            continue

                                        if any(x in inner_text for x in ["espera", "generando", "por favor"]):
                                            continue
                                            
                                        if float(opacity) > 0.4:
                                            self.log("STEP7", f"Target found: '{inner_text}' in {url[:30]}. Clicking...")
                                            
                                            try:
                                                # Tomar screenshot antes del click final por si falla
                                                if "ingresa" in inner_text or "vínculo" in inner_text:
                                                     p.screenshot(path=f"logs/step7_target_found_{int(time.time())}.png")

                                                res = self._wait_for_new_page(p, lambda: btn.click(force=True, timeout=8000))
                                                if isinstance(res, dict): return res
                                                
                                                if res and any(x in res.url.lower() for x in ["drive.google", "mega.nz", "mediafire", "1fichier"]):
                                                    return {"url": res.url}
                                                
                                                # Si después de clickear "Continuar" abrió otra cosa de saboresmexico, genial.
                                                # Si abrió basura, cerrarla.
                                                if res and res != p:
                                                     if "saboresmexico" not in res.url:
                                                          try: res.close()
                                                          except: pass
                                            except: pass
                                except: continue
                        except: continue

                    # 4. Buscar links directos en el DOM de esta página
                    patterns = ["a[href*='drive.google.com']", "a[href*='mega.nz']", "a[href*='mediafire.com']", "a[href*='googledrive.com']"]
                    for pat in patterns:
                        try:
                            # Buscar en cada frame el link directo
                            for frame in p.frames:
                                el = frame.query_selector(pat)
                                if el:
                                    href = el.get_attribute("href")
                                    if href and "saboresmexico" not in href:
                                        self.log("STEP7", f"Found direct link in tab {url[:30]}: {href[:60]}")
                                        return {"url": href}
                        except: continue

                    # 6. Fallback final: revisar si el href de la página misma cambió a un proveedor
                    if any(x in url for x in ["drive.google.com", "mega.nz", "mediafire.com"]):
                         return {"url": p.url}

                    # 5. Si es saboresmexico, hacer scroll suave para despertar el script
                    if "saboresmexico" in url and int(time.time()) % 10 == 0:
                        try:
                            p.mouse.wheel(0, 200)
                            p.wait_for_timeout(100)
                            p.mouse.wheel(0, -200)
                        except: pass
                        
                except: continue

            # Simulación de espera/interacción si no hay nada
            elapsed = int(time.time() - start_time)
            if elapsed % 20 == 0:
                self.log("STEP7", f"Still looking for link... {elapsed}s")
            
            # Usar el contexto para esperar si la página fue cerrada
            try:
                if not page.is_closed():
                    page.wait_for_timeout(2000)
                else:
                    time.sleep(2) # Fallback si la página principal murió
            except:
                time.sleep(2)
            
        return None

    def _close_trash_tabs(self, main_page: Page):
        for p in self.context.pages:
            try:
                if p == main_page: continue
                if p.is_closed(): continue
                
                url = p.url.lower()
                
                # NUNCA cerrar saboresmexico.com durante el proceso, 
                # ya que el link final puede aparecer en cualquiera de sus pestañas abiertas
                if "saboresmexico.com" in url:
                    continue

                # Whitelist expandida
                good_keywords = [
                    "mediafire.com", "mega.nz", "1fichier.com", "drive.google.com", 
                    "googledrive.com", "google.com/sorry",
                    "peliculasgd"
                ]
                
                if any(k in url for k in good_keywords):
                    continue
                
                # No cerrar si es una página de descarga conocida
                if any(x in url for x in ["download", "file", "sh."]):
                    continue

                self.log("DEBUG", f"Closing trash tab: {url[:50]}...")
                p.close()
            except: pass

    def _detect_provider(self, url: str) -> str:
        if "drive.google" in url: return "GoogleDrive"
        if "mega.nz" in url: return "Mega"
        if "mediafire" in url: return "MediaFire"
        return "Unknown"

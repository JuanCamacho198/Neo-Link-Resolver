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
        
        # Esperar a que se quite el redirector href.li y manejar CAPTCHA
        try:
            page.wait_for_url("**/google.com/*", timeout=15000)
        except:
            self.log("WARNING", f"Never reached Google. Current URL: {page.url}")

        # SI HAY CAPTCHA, avisar y esperar un poco más por si el usuario lo resuelve
        if "google.com/sorry" in page.url:
            self.log("WARNING", "Google CAPTCHA detected! Please solve it in the browser or wait...")
            # Intentar clickear el primer link que no sea de google si aparece algo
            page.wait_for_timeout(5000)
            
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        
        # Aceptar cookies de Google si aparecen
        try:
            page.evaluate("() => { document.querySelectorAll('button').forEach(b => { if(b.innerText.includes('Aceptar') || b.innerText.includes('Accept all')) b.click(); })}")
        except: pass

        # Intentar varios selectores para el primer resultado
        selectors = [
            "#search a h3",
            "a h3",
            "#rso a[href*='saboresmexico.com']", # Específico para este caso
            "#rso a h3"
        ]
        
        target = None
        start_wait = time.time()
        while time.time() - start_wait < 30: # Esperar hasta 30s por el resultado
            for sel in selectors:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        target = page.evaluate_handle("el => el.closest('a')", el).as_element()
                        if target:
                            self.log("STEP4", f"Found result with selector: {sel}")
                            return self._wait_for_new_page(page, lambda: target.click())
                except: continue
            
            if "google.com/sorry" in page.url:
                self.log("STEP4", "Still blocked by CAPTCHA...")
            page.wait_for_timeout(2000)
        
        # Si fallamos Google, intentar ir directo si tenemos la URL en el query (FALLBACK SABORESMEXICO)
        try:
            if "google.com/sorry" in page.url or "google.com" in page.url:
                import urllib.parse
                parsed = urllib.parse.urlparse(page.url)
                params = urllib.parse.parse_qs(parsed.query)
                q = params.get('q', [''])[0]
                # Limpiar el site:saboresmexico.com del query
                clean_q = q.replace('site:saboresmexico.com', '').strip()
                if clean_q:
                    self.log("STEP4", f"Google blocked. Using direct search fallback on saboresmexico.com for: {clean_q}")
                    page.goto(f"https://saboresmexico.com/?s={urllib.parse.quote(clean_q)}")
                    page.wait_for_load_state("domcontentloaded")
                    # Buscar el primer artículo en los resultados de búsqueda de la web
                    first_article = page.query_selector("article a, .entry-title a")
                    if first_article:
                        self.log("STEP4", "Found article via direct site search!")
                        return self._wait_for_new_page(page, lambda: first_article.click())
        except Exception as e:
            self.log("DEBUG", f"Direct search fallback failed: {e}")

        page.screenshot(path="logs/peliculasgd_google_fail.png")
        raise Exception("Google search results not found or blocked by CAPTCHA")

    def _step5_6_resolve_verification_and_timer(self, page: Page) -> Page:
        self.log("STEP5/6", "Resolving blog verification (timer + ad click)...")
        
        # Eliminar cookies DE INMEDIATO y de forma agresiva
        def kill_cookies():
            try:
                page.evaluate("""() => {
                    const selectors = [
                        '.fc-consent-root', '.cc-window', '#onetrust-consent-sdk', 
                        '[id*="google-consent"]', '.asap-cookie-consent', 
                        '.cmplz-cookiebanner', '.cmplz-blocked-content-notice',
                        '#cmplz-cookiebanner-container', '.cmplz-soft-cookiewall'
                    ];
                    selectors.forEach(sel => {
                        const els = document.querySelectorAll(sel);
                        els.forEach(el => el.remove());
                    });
                    const acceptBtn = document.querySelector('.cmplz-btn.cmplz-accept, .cc-btn.cc-allow, #onetrust-accept-btn-handler');
                    if (acceptBtn) acceptBtn.click();
                    document.body.style.overflow = 'auto';
                    document.documentElement.style.overflow = 'auto';
                }""")
            except: pass

        kill_cookies()
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        kill_cookies()

        # Simulación humana intensiva inicial
        self.log("STEP5/6", "Simulating human interaction to trigger verification script...")
        simulate_human_behavior(page, intensity="heavy")
        
        start_time = time.time()
        ad_clicked = False
        
        while time.time() - start_time < 180:
            if page.is_closed():
                # Intentar recuperar si hay otra página de saboresmexico abierta
                found_alternate = False
                for p in self.context.pages:
                    if not p.is_closed() and "saboresmexico.com" in p.url:
                        self.log("DEBUG", "Current page closed. Switching to alternate saboresmexico tab.")
                        page = p
                        found_alternate = True
                        break
                if not found_alternate:
                    self.log("DEBUG", "Page closed and no alternate found.")
                    break

            kill_cookies() # Seguir matando popups que reaparezcan

            # 1. Buscar el botón de continuar
            found_any_potential = False
            for frame in page.frames:
                if page.is_closed(): break
                try:
                    # Selectores de botones de este blog específico
                    selectors = [
                        "button:has-text('Continuar')", 
                        "a:has-text('Continuar')",
                        "button:has-text('Obtener Vínculo')",
                        "a:has-text('Obtener Vínculo')",
                        "button:has-text('Ir al enlace')",
                        "a:has-text('Ir al enlace')",
                        "button:has-text('Get Link')",
                        "a:has-text('Get Link')",
                        "a[href*='saboresmexico.com/postres']", 
                        ".button-s",
                        "a.btn-link",
                        "#generar_link",
                        ".get-link"
                    ]
                    
                    for sel in selectors:
                        try:
                            # Buscar SIEMPRE, incluso si no es visible aún para debug
                            btn = frame.query_selector(sel)
                            if btn:
                                found_any_potential = True
                                if btn.is_visible():
                                    inner_text = (btn.inner_text() or "").lower()
                                    opacity = btn.evaluate("el => getComputedStyle(el).opacity")
                                    is_disabled = btn.get_attribute("disabled") is not None
                                    
                                    # Si el botón es visible y activo, CLICK
                                    if not is_disabled and float(opacity) > 0.5: # Bajamos un poco el umbral de opacidad por si acaso
                                        self.log("STEP5/6", f"Found active button: '{inner_text}' via {sel}")
                                        # Capturar si abre nueva pestaña
                                        try:
                                            return self._wait_for_new_page(page, lambda: btn.click(force=True, timeout=5000))
                                        except:
                                            # Si no abrió nueva pestaña pero navegó, _wait_for_new_page lo maneja si devolvemos el mismo tab
                                            return page
                        except: continue
                except: continue

            elapsed = time.time() - start_time
            
            # Autocompensación: si detectamos que estamos en un loop infinito y no hay ad_clicked, re-intentar sidebar
            if elapsed > 45 and not ad_clicked:
                ad_clicked = False # Reset para forzar otro clic
            
            # 2. Clic en sidebar REAL (evitando ads de MGID/sponsored)
            if not ad_clicked and elapsed > 2.0:
                try:
                    sidebar_article_links = page.query_selector_all(".last-post-sidebar a, .article-loop a")
                    
                    target_link = None
                    for link in sidebar_article_links:
                        try:
                            # Verificar que NO sea un ad de MGID o similar
                            is_ad = page.evaluate("""(el) => {
                                let curr = el;
                                while(curr && curr !== document.body) {
                                    const cls = (curr.className || "").toString().toLowerCase();
                                    const id = (curr.id || "").toString().toLowerCase();
                                    if (cls.includes('mgbox') || cls.includes('mgline') || cls.includes('teaser') || 
                                        cls.includes('sponsored') || id.includes('mgid')) return true;
                                    curr = curr.parentElement;
                                }
                                return false;
                            }""", link)
                            if not is_ad and link.is_visible():
                                target_link = link
                                break
                        except: continue

                    if target_link:
                        self.log("STEP5/6", f"Clicking REAL sidebar article to trigger verification: {target_link.get_attribute('href')}")
                        target_link.click(force=True, timeout=3000)
                        ad_clicked = True
                        page.wait_for_timeout(3000) # Dejar que cargue la navegación
                except Exception as e:
                    self.log("DEBUG", f"Error clicking sidebar: {e}")

            # 3. Interacciones periódicas
            if int(elapsed) % 15 == 0: 
                try: 
                    if not page.is_closed():
                        page.mouse.wheel(0, 100)
                        page.wait_for_timeout(100)
                        page.mouse.wheel(0, -100)
                except: pass

            try:
                if not page.is_closed():
                    page.wait_for_timeout(500) 
                else: break
            except: break

            if int(elapsed) % 10 == 0:
                self._close_trash_tabs(page) # Limpiar cada 10s solamente
                current_url = page.url.split('?')[0][-40:] # Mostrar final de URL
                self.log("STEP5/6", f"Status: {current_url} | {int(elapsed)}s")
            
        raise Exception("Failed to resolve human verification (button never became active)")

    def _step7_extract_final_link(self, page: Page) -> Optional[Dict]:
        self.log("STEP7", "Extracting final link...")
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        
        # Simulación humana inicial
        simulate_human_behavior(page, intensity="low")
        
        start_time = time.time()
        while time.time() - start_time < 60: # 60s para el paso final
            if page.is_closed(): break
            
            # Matar cookies/popups de nuevo
            self.log("STEP7", f"Waiting for final link... {int(time.time() - start_time)}s")
            try:
                page.evaluate("() => { const b = document.querySelector('.fc-consent-root, .cmplz-cookiebanner'); if(b) b.remove(); }")
            except: pass

            url = page.url.lower()
            
            # 1. Si ya estamos en un link de almacenamiento, lo devolvemos
            if any(prov in url for prov in ["drive.google.com", "mega.nz", "mediafire.com", "1fichier.com"]):
                return {"url": page.url}
                
            # 2. Buscar botones en TODOS los frames
            for frame in page.frames:
                try:
                    selectors = [
                        "a:has-text('Obtener Vínculo')", 
                        "button:has-text('Obtener Vínculo')",
                        "a:has-text('Ir al enlace')", 
                        "button:has-text('Ir al enlace')",
                        "a:has-text('Continuar')",
                        "button:has-text('Continuar')",
                        "a:has-text('Descargar Aqui')", 
                        "a.btn-download",
                        "a.btn-link",
                        "#generar_link"
                    ]
                    for sel in selectors:
                        try:
                            btn = frame.query_selector(sel)
                            if btn and btn.is_visible():
                                inner_text = (btn.inner_text() or "").lower()
                                opacity = btn.evaluate("el => getComputedStyle(el).opacity")
                                # Si dice "espera", no clickear aún
                                if "espera" in inner_text or "generando" in inner_text:
                                    continue
                                if float(opacity) > 0.5:
                                    self.log("STEP7", f"Found active link button '{inner_text}' in frame. Clicking...")
                                    # Intentar clickear y esperar nueva página o navegación
                                    try:
                                        return self._wait_for_new_page(page, lambda: btn.click(force=True, timeout=5000))
                                    except: pass
                        except: continue
                except: continue

            # 3. Buscar en el DOM links directos (Mediafire, Mega, etc.)
            patterns = [
                "a[href*='drive.google.com']",
                "a[href*='mega.nz']",
                "a[href*='mediafire.com']",
                "a[href*='1fichier.com']",
                "a[href*='googledrive.com']"
            ]
            for p in patterns:
                try:
                    el = page.query_selector(p)
                    if el:
                        href = el.get_attribute("href")
                        if href and not "saboresmexico" in href: # Evitar links internos
                            self.log("STEP7", f"Found direct link in DOM: {href[:60]}")
                            return {"url": href}
                except: continue

            # 4. Regex como último recurso
            try:
                content = page.content()
                matches = re.findall(r'https?://(?:mega\.nz|drive\.google\.com|mediafire\.com|1fichier\.com|googledrive\.com)/[^\s"\'<>]+', content)
                for m in matches:
                    if "saboresmexico" not in m:
                        self.log("STEP7", f"Found link via regex: {m[:60]}")
                        return {"url": m}
            except: pass

            page.wait_for_timeout(2000)
            
        page.screenshot(path="logs/peliculasgd_step7_fail.png")
        return None

    def _close_trash_tabs(self, main_page: Page):
        for p in self.context.pages:
            try:
                if p == main_page: continue
                if p.is_closed(): continue
                
                url = p.url.lower()
                # Whitelist expandida
                good_keywords = [
                    "mediafire.com", "mega.nz", "1fichier.com", "drive.google.com", 
                    "googledrive.com", "saboresmexico.com", "google.com/sorry",
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

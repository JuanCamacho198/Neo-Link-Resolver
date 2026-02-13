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
            if "google.com/sorry" in page.url:
                self.log("WARNING", "Google CAPTCHA detected. Waiting 5s...")
                page.wait_for_timeout(5000)
        except:
            self.log("WARNING", f"Never reached Google. Current URL: {page.url}")

        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        
        # Aceptar cookies de Google si aparecen
        try:
            page.evaluate("() => { document.querySelectorAll('button').forEach(b => { if(b.innerText.includes('Aceptar') || b.innerText.includes('Accept all')) b.click(); })}")
        except: pass

        # Intentar varios selectores para el primer resultado
        selectors = [
            "#search a h3",
            "a h3",
            "#rso a[href]:not([href*='google']) h3",
            "#rso a h3"
        ]
        
        target = None
        for sel in selectors:
            try:
                el = page.wait_for_selector(sel, timeout=10000)
                if el:
                    target = page.evaluate_handle("el => el.closest('a')", el).as_element()
                    if target:
                        self.log("STEP4", f"Found result with selector: {sel}")
                        break
            except: continue
        
        if not target:
            # Screenshot de debug
            page.screenshot(path="logs/peliculasgd_google_fail.png")
            raise Exception("Google search results not found")
            
        return self._wait_for_new_page(page, lambda: target.click())

    def _step5_6_resolve_verification_and_timer(self, page: Page) -> Page:
        self.log("STEP5/6", "Resolving blog verification (timer + ad click)...")
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        
        # --- Limpieza de overlays ---
        try:
            page.evaluate("""() => {
                ['.fc-consent-root', '.cc-window', '#onetrust-consent-sdk', '[id*="google-consent"]'].forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
                document.body.style.overflow = 'auto';
            }""")
        except: pass

        # Simulación humana intensiva inicial
        self.log("STEP5/6", "Simulating human interaction to trigger verification script...")
        simulate_human_behavior(page, intensity="heavy")
        
        start_time = time.time()
        ad_clicked = False
        
        while time.time() - start_time < 180:
            if page.is_closed():
                break

            # --- Limpieza de overlays (reiterativa) ---
            try:
                page.evaluate("""() => {
                    [
                        '.fc-consent-root', '.cc-window', '#onetrust-consent-sdk', 
                        '[id*="google-consent"]', '.asap-cookie-consent', 
                        '.cmplz-cookiebanner', '.cmplz-blocked-content-notice',
                        '#cmplz-cookiebanner-container'
                    ].forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => el.remove());
                    });
                    // Intentar clickar el botón de aceptar si existe y no se ha borrado
                    const acceptBtn = document.querySelector('.cmplz-btn.cmplz-accept');
                    if (acceptBtn) acceptBtn.click();
                    
                    document.body.style.overflow = 'auto';
                }""")
            except: pass

            # 1. Buscar en TODOS los marcos (iframes) el botón
            for frame in page.frames:
                try:
                    # Log si vemos el texto de verificación
                    v_text = frame.query_selector("text='Verificando que eres un humano'")
                    if v_text:
                        progress = frame.query_selector("text='%'")
                        self.log("STEP5/6", f"Verification widget detected! Progress: {progress.inner_text() if progress else '???'}")

                    selectors = [
                        "button:has-text('Continuar')", 
                        "a:has-text('Continuar')",
                        "button:has-text('Obtener Vínculo')",
                        "a:has-text('Obtener Vínculo')",
                        "a[href*='saboresmexico.com/postres']", 
                        ".button-s",
                        "a.btn-link"
                    ]
                    
                    for sel in selectors:
                        btn = frame.query_selector(sel)
                        if btn and btn.is_visible():
                            try:
                                inner_text = (btn.inner_text() or "").lower()
                                opacity = btn.evaluate("el => getComputedStyle(el).opacity")
                                is_disabled = btn.get_attribute("disabled") is not None
                                
                                if ("continuar" in inner_text or "vínculo" in inner_text or "vinculo" in inner_text or "btn" in sel) and not is_disabled and float(opacity) > 0.8:
                                    self.log("STEP5/6", f"Found active button: '{inner_text}'")
                                    return self._wait_for_new_page(page, lambda: btn.click())
                            except: continue
                except: continue

            # 2. Interacciones periódicas
            elapsed = time.time() - start_time
            if int(elapsed) % 20 == 0:
                try:
                    page.mouse.move(random.randint(100, 700), random.randint(100, 500))
                except: pass

            # 3. Clic en "Artículos relacionados" (pista del usuario) para activar el script de verificación
            if not ad_clicked and elapsed > 10:
                try:
                    # Buscamos artículos en el sidebar o loops de artículos que suelen disparar el popup
                    sidebar_links = page.query_selector_all(".last-post-sidebar a, .article-loop a, .asap-posts-loop a")
                    if sidebar_links:
                        self.log("STEP5/6", f"Clicking sidebar article to trigger verification (User Tip)...")
                        # Elegimos uno al azar o el primero
                        target_link = random.choice(sidebar_links[:3])
                        target_link.click()
                        ad_clicked = True # Marcamos como que ya interactuamos "fuertemente"
                        page.wait_for_timeout(3000)
                        self._close_trash_tabs(page)
                except: pass

            # 4. Clic en Ad si lo anterior no funcionó
            if elapsed > 30 and not ad_clicked:
                try:
                    ads = page.query_selector_all("ins.adsbygoogle, iframe[src*='googleads'], #click_message")
                    visible_ads = [ad for ad in ads if ad.is_visible()]
                    if visible_ads:
                        self.log("STEP5/6", "Clicking ad to trigger progress...")
                        visible_ads[0].click()
                        ad_clicked = True
                        page.wait_for_timeout(3000)
                        self._close_trash_tabs(page)
                except: pass
                    
            page.wait_for_timeout(2000)
            self.log("STEP5/6", f"Status: waiting for verification... {int(time.time() - start_time)}s")
            
        raise Exception("Failed to resolve human verification (button never became active)")

    def _step7_extract_final_link(self, page: Page) -> Optional[Dict]:
        self.log("STEP7", "Extracting final link...")
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        
        # Simulación humana para cargar contenido dinámico
        simulate_human_behavior(page, intelligence="low")
        
        start_time = time.time()
        while time.time() - start_time < 30:
            url = page.url.lower()
            
            # 1. Si ya estamos en un link de almacenamiento, lo devolvemos
            if any(prov in url for prov in ["drive.google.com", "mega.nz", "mediafire.com", "1fichier.com"]):
                return {"url": page.url}
                
            # 2. Buscar botones de "Obtener Vínculo" o "Descargar"
            try:
                selectors = ["a:has-text('Obtener Vínculo')", "button:has-text('Obtener Vínculo')", "a:has-text('Descargar Aqui')", "a.btn-download"]
                for sel in selectors:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        opacity = btn.evaluate("el => getComputedStyle(el).opacity")
                        if float(opacity) > 0.8:
                            self.log("STEP7", f"Found link button '{btn.inner_text()}'. Clicking...")
                            return self._wait_for_new_page(page, lambda: btn.click())
            except: pass

            # 3. Buscar en el DOM links rectos
            patterns = [
                "a[href*='drive.google.com']",
                "a[href*='mega.nz']",
                "a[href*='mediafire.com']",
                "a[href*='1fichier.com']"
            ]
            for p in patterns:
                try:
                    el = page.query_selector(p)
                    if el:
                        href = el.get_attribute("href")
                        if href:
                            self.log("STEP7", f"Found direct link: {href[:60]}")
                            return {"url": href}
                except: continue

            # 4. Fallback Regex
            content = page.content()
            matches = re.findall(r'https?://(?:mega\.nz|drive\.google\.com|mediafire\.com|1fichier\.com|googledrive\.com)/[^\s"\'<>]+', content)
            if matches:
                 self.log("STEP7", f"Found link via regex: {matches[0][:60]}")
                 return {"url": matches[0]}

            page.wait_for_timeout(2000)
            
        page.screenshot(path="logs/peliculasgd_step7_fail.png")
        return None

    def _close_trash_tabs(self, main_page: Page):
        for p in self.context.pages:
            try:
                if p != main_page and not p.is_closed():
                    url = p.url.lower()
                    # Whitelist de lo que NO queremos cerrar
                    if any(d in url for d in ["mediafire.com", "mega.nz", "1fichier.com", "drive.google.com", "googledrive.com"]):
                        continue
                    
                    # Si no es nulo/blanco y no es el principal, cerrar
                    if url != "about:blank" and url != "chrome-error://chromewebdata/":
                        self.log("DEBUG", f"Closing trash tab: {url[:50]}...")
                        p.close()
            except: pass

    def _detect_provider(self, url: str) -> str:
        if "drive.google" in url: return "GoogleDrive"
        if "mega.nz" in url: return "Mega"
        if "mediafire" in url: return "MediaFire"
        return "Unknown"

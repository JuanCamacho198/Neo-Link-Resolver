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
        
        # Esperar a que se quite el redirector href.li
        try:
            page.wait_for_url("**/google.com/search*", timeout=15000)
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
            # 1. Buscar en TODOS los marcos (iframes) el botón
            all_frames = page.frames
            for frame in all_frames:
                try:
                    # Selectores de botones de continuar
                    selectors = [
                        "button:has-text('Continuar')", 
                        "a:has-text('Continuar')",
                        "div:has-text('Continuar')",
                        "button:has-text('Obtener Vínculo')",
                        "a:has-text('Obtener Vínculo')",
                        "button.button-s"
                    ]
                    
                    for sel in selectors:
                        btn = frame.query_selector(sel)
                        if btn and btn.is_visible():
                            # Comprobar si realmente dice "Continuar" (case insensitive)
                            inner_text = btn.inner_text().lower()
                            if "continuar" in inner_text or "vínculo" in inner_text or "vinculo" in inner_text:
                                is_disabled = btn.get_attribute("disabled") is not None
                                opacity = btn.evaluate("el => getComputedStyle(el).opacity")
                                
                                # Si tiene opacidad baja, es que el timer no terminó
                                if not is_disabled and float(opacity) > 0.8:
                                    self.log("STEP5/6", f"Found active button in frame: '{inner_text}'")
                                    return self._wait_for_new_page(page, lambda: btn.click())
                except: continue

            # 2. Si no lo encontramos habilitado, forzar interacciones
            if (time.time() - start_time) % 20 < 5:
                self.log("STEP5/6", "Interacting with page (move/click random) to satisfy humansim check...")
                page.mouse.move(100, 100)
                page.mouse.move(500, 500)
                page.mouse.click(300, 300)
                page.evaluate("window.scrollBy(0, 300)")
                random_delay(1, 2)
                page.evaluate("window.scrollBy(0, -300)")

            # 3. Clic en Ad si es necesario
            if not ad_clicked and (time.time() - start_time) > 20:
                self.log("STEP5/6", "Clicking ad area to start/accelerate timer...")
                ads = page.query_selector_all("ins.adsbygoogle, iframe[src*='googleads'], #click_message")
                for ad in ads:
                    if ad.is_visible():
                        try:
                            ad.click()
                            ad_clicked = True
                            page.wait_for_timeout(3000)
                            self._close_trash_tabs(page)
                            break
                        except: continue

            # Acelerar timers
            if self.timer_interceptor:
                self.timer_interceptor.accelerate_timers(page)
                self.timer_interceptor.skip_peliculasgd_timer(page)

            page.wait_for_timeout(5000)
            self.log("STEP5/6", f"Status: waiting for verification... {int(time.time() - start_time)}s")
            
        raise Exception("Failed to resolve human verification (button never became active)")

    def _step7_extract_final_link(self, page: Page) -> Optional[Dict]:
        self.log("STEP7", "Extracting final link...")
        # Darle un margen para cargar
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        random_delay(2.0, 4.0)
        
        url = page.url.lower()
        self.log("STEP7", f"Current URL after verification: {url[:70]}...")

        # 1. Si ya estamos en un link de almacenamiento, lo devolvemos
        if any(prov in url for prov in ["drive.google.com", "mega.nz", "mediafire.com", "1fichier.com"]):
            return {"url": page.url}
            
        # 2. Buscar en el DOM todos los links que parezcan de almacenamiento
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
                    if href:
                        self.log("STEP7", f"Found link in DOM: {href[:60]}")
                        return {"url": href}
            except: continue
                
        # 3. Buscar links en el contenido de texto (regex)
        content = page.content()
        matches = re.findall(r'https?://(?:mega\.nz|drive\.google\.com|mediafire\.com|1fichier\.com|googledrive\.com)/[^\s"\'<>]+', content)
        if matches:
            self.log("STEP7", f"Found link via regex in content: {matches[0][:60]}")
            return {"url": matches[0]}
            
        # 4. Escaneo de tráfico de red (si se capturó algo)
        if self.network_analyzer and self.network_analyzer.captured_links:
            best = self.network_analyzer.get_best_link()
            if best:
                self.log("STEP7", f"Retrieved link from network capture: {best[:60]}")
                return {"url": best}
        
        # 5. Captura final de debug si fallamos
        page.screenshot(path="logs/peliculasgd_step7_fail.png")
        return None

    def _close_trash_tabs(self, main_page: Page):
        for p in self.context.pages:
            if p != main_page and not p.is_closed():
                url = p.url.lower()
                if not any(d in url for d in ["google", "peliculasgd", "mediafire", "mega", "drive"]):
                    p.close()

    def _detect_provider(self, url: str) -> str:
        if "drive.google" in url: return "GoogleDrive"
        if "mega.nz" in url: return "Mega"
        if "mediafire" in url: return "MediaFire"
        return "Unknown"

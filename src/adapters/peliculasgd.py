"""
adapters/peliculasgd.py - Adaptador para peliculasgd.net
Implementa el flujo completo de 7 pasos documentado en PLAN.md
"""

from typing import List
from playwright.sync_api import Page
from .base import SiteAdapter
from matcher import LinkOption, LinkMatcher
from config import TIMEOUT_NAV, TIMEOUT_ELEMENT, AD_WAIT_SECONDS
from human_sim import random_delay, simulate_human_behavior, human_mouse_move
from url_parser import extract_metadata_from_url
import time


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
            page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAV)
            page.screenshot(path="peliculasgd_step0_movie.png")

            # Step 1: Click "Enlaces Publicos"
            intermediate1 = self._step1_click_enlaces_publicos(page)
            intermediate1.screenshot(path="peliculasgd_step1_inter1.png")

            # Step 2: Click "Haz clic aqui"
            intermediate2 = self._step2_click_haz_clic_aqui(intermediate1)
            intermediate2.screenshot(path="peliculasgd_step2_inter2.png")

            # Step 3: Click "CLIC AQUI PARA CONTINUAR"
            google_page = self._step3_click_continuar(intermediate2)
            google_page.screenshot(path="peliculasgd_step3_google.png")

            # Step 4: Click primer resultado de Google
            verification_page = self._step4_click_first_google_result(google_page)
            verification_page.screenshot(path="peliculasgd_step4_verif.png")

            # Step 5: Verificacion humana
            self._step5_human_verification(verification_page)
            verification_page.screenshot(path="peliculasgd_step5_after.png")

            # Step 6: Click ad + esperar
            self._step6_click_ad_and_wait(verification_page)
            verification_page.screenshot(path="peliculasgd_step6_after.png")

            # Step 7: Volver a intermediate1 y obtener link
            final_link = self._step7_return_to_intermediate()

            # Extraer metadata de la URL original (calidad, formato, idioma)
            url_metadata = extract_metadata_from_url(url)
            self.log("METADATA", f"Extracted from URL: quality={url_metadata['quality']}, format={url_metadata['format']}, lang={url_metadata['language']}")

            # Crear LinkOption para el link final
            link_option = LinkOption(
                url=final_link,
                text=f"PeliculasGD - {url_metadata['quality'] or 'N/A'} {url_metadata['format'] or ''}",
                provider=self._detect_provider(final_link),
                quality=url_metadata['quality'] or "",
                format=url_metadata['format'] or ""
            )

            self.log("RESULT", f"Resolved: {link_option.url[:100]}")
            return link_option

        except Exception as e:
            self.log("ERROR", f"Failed: {e}")
            # Screenshots de debug
            for i, p_tab in enumerate(self.context.pages):
                if not p_tab.is_closed():
                    p_tab.screenshot(path=f"peliculasgd_error_tab{i}.png")
            raise

        finally:
            page.close()

    # ---------------------------------------------------------------------------
    # Implementacion de los 7 pasos (del main.py original)
    # ---------------------------------------------------------------------------

    def _wait_for_new_page(self, page: Page, trigger_action, timeout=40_000) -> Page:
        """
        Ejecuta accion que abre nueva pestana y la retorna.
        """
        self.log("NAV", "Interacting to find next target page...")
        
        for attempt in range(4): 
            self.log("DEBUG", f"Click attempt {attempt + 1}...")
            
            # Limpiar overlays
            try:
                page.evaluate("() => { document.querySelectorAll('.fixed, [class*=\"overlay\"]').forEach(el => el.remove()); }")
            except: pass

            try:
                with self.context.expect_page(timeout=10000) as new_page_info:
                    trigger_action()
                
                new_page = new_page_info.value
                new_page.wait_for_load_state("domcontentloaded", timeout=10000)
                url = new_page.url.lower()
                
                trash_domains = [
                    "mexicodesconocido", "gourmetdemexico", "asociaciondemexico", 
                    "traveler", "realsite", "doubleclick", "adnxs", "popads", 
                    "onclick", "bet", "gamble", "href.li", "about:blank"
                ]
                
                # neworldtravel y saboresmexico son parte del flujo de PeliculasGD
                is_trash = any(domain in url for domain in trash_domains)
                
                if is_trash and "google.com/search" not in url:
                    self.log("DEBUG", f"Closing real ad popup: {url[:40]}")
                    new_page.close()
                    random_delay(1.0, 2.0)
                    continue
                else:
                    self.log("NAV", f"Target page detected: {url[:60]}")
                    return new_page
            except Exception as e:
                self.log("WARNING", f"Attempt {attempt+1} failed: {e}")
                random_delay(1.0, 2.0)
                
        raise Exception("Failed to find a valid new page in PeliculasGD chain")

    def _step1_click_enlaces_publicos(self, page: Page) -> Page:
        self.log("STEP1", "Looking for 'Enlaces Publicos'...")
        # Asegurar scroll
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        
        selectors = [
            "a:has(img.wp-image-125438)",
            "a:has(img[src*='cxx'])",
            "a:has(img[alt*='enlace' i])",
            "img.wp-image-125438",
            "xpath=//strong[contains(text(), 'Enlaces Públicos')]/preceding-sibling::a[1]",
            "xpath=//strong[contains(text(), 'Enlaces Públicos')]/parent::a",
        ]
        
        target = None
        for sel in selectors:
            target = page.query_selector(sel)
            if target:
                self.log("DEBUG", f"Found element with selector: {sel}")
                break
        
        if not target:
            # Screenshot de debug si no lo encuentra
            page.screenshot(path="logs/peliculasgd_step1_not_found.png")
            raise Exception("Enlaces Publicos link not found")
            
        return self._wait_for_new_page(page, lambda: target.click())

    def _step2_click_haz_clic_aqui(self, page: Page) -> Page:
        self.log("STEP2", "Looking for 'Haz clic aqui'...")
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        random_delay(1.0, 3.0)
        selectors = [
            "div.text >> text='Haz clic aquí'",
            "div.text >> text='Haz clic aqui'",
            "text='Haz clic aquí'",
            "a:has-text('Haz clic aquí')",
        ]
        target = None
        for sel in selectors:
            try:
                target = page.wait_for_selector(sel, timeout=TIMEOUT_ELEMENT)
                if target:
                    break
            except Exception:
                continue
        if not target:
            raise Exception("'Haz clic aqui' not found")
        random_delay(0.5, 1.0)
        return self._wait_for_new_page(page, lambda: target.click())

    def _step3_click_continuar(self, page: Page) -> Page:
        self.log("STEP3", "Looking for 'CLIC AQUI PARA CONTINUAR'...")
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        random_delay(1.0, 3.0)
        selectors = [
            "button.button-s:has-text('CLIC')",
            "button.button-s",
            "a.button-s",
        ]
        button = None
        for sel in selectors:
            try:
                button = page.wait_for_selector(sel, timeout=TIMEOUT_ELEMENT)
                if button:
                    break
            except Exception:
                continue
        if not button:
            raise Exception("Continue button not found")
        random_delay(0.5, 1.5)
        return self._wait_for_new_page(page, lambda: button.click())

    def _step4_click_first_google_result(self, page: Page) -> Page:
        self.log("STEP4", "Clicking first Google result...")
        
        # Esperar a que Google cargue de verdad (si viene de href.li)
        try:
            page.wait_for_url("**/google.com/search*", timeout=15000)
        except:
            self.log("WARNING", f"Timeout waiting for Google URL. Current: {page.url}")
            
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        random_delay(1.5, 3.0)
        
        # Limpiar posibles overlays de cookies en Google
        try:
            page.evaluate("() => { document.querySelectorAll('button:has-text(\"Aceptar\"), button:has-text(\"Accept all\")').forEach(b => b.click()); }")
        except: pass

        selectors = [
            "a h3",
            "#search a[href]:not([href*='google'])",
            "#rso a[href]:not([href*='google'])",
        ]
        first_result = None
        for sel in selectors:
            try:
                el = page.wait_for_selector(sel, timeout=5000)
                if el:
                    # Si es un h3, queremos el padre <a>
                    if el.evaluate("el => el.tagName === 'H3'"):
                        first_result = page.evaluate_handle("el => el.closest('a')", el).as_element()
                    else:
                        first_result = el
                    break
            except:
                continue
                
        if not first_result:
            # Screenshot de debug
            page.screenshot(path="logs/peliculasgd_google_fail.png")
            raise Exception("Google first result not found")
            
        random_delay(0.5, 1.5)
        return self._wait_for_new_page(page, lambda: first_result.click())

    def _step5_human_verification(self, page: Page):
        self.log("STEP5", "Human verification - simulating behavior...")
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        random_delay(2.0, 4.0)
        simulate_human_behavior(page, intensity="heavy")
        random_delay(2.0, 4.0)
        simulate_human_behavior(page, intensity="normal")
        random_delay(1.0, 3.0)

        # Click "Continuar"
        selectors = [
            "button.button-s:has-text('Continuar')",
            "button:has-text('Continuar')",
        ]
        continuar_btn = None
        for sel in selectors:
            try:
                continuar_btn = page.wait_for_selector(sel, timeout=TIMEOUT_ELEMENT)
                if continuar_btn:
                    break
            except Exception:
                continue
        if not continuar_btn:
            raise Exception("Continuar button not found")
        random_delay(0.5, 1.5)
        continuar_btn.click()
        random_delay(2.0, 5.0)

    def _step6_click_ad_and_wait(self, page: Page):
        self.log("STEP6", "Looking for mandatory ad...")
        try:
            page.wait_for_selector("#click_message", state="visible", timeout=TIMEOUT_ELEMENT)
        except Exception:
            self.log("STEP6", "Warning: #click_message not found")

        random_delay(1.0, 3.0)

        # Click en ad
        ad_selectors = [
            "#click_message ~ *",
            "iframe[src*='ad']",
            "ins.adsbygoogle",
        ]
        ad_clicked = False
        for sel in ad_selectors:
            ad = page.query_selector(sel)
            if ad and ad.is_visible():
                try:
                    ad.click()
                    ad_clicked = True
                    self.log("STEP6", "Clicked ad")
                    break
                except Exception:
                    continue

        if not ad_clicked:
            viewport = page.viewport_size or {"width": 1280, "height": 720}
            page.mouse.click(viewport["width"] // 2, viewport["height"] - 150)

        random_delay(2.0, 4.0)
        self._close_unwanted_popups([page])

        # Aceleración de Timer (Novedad)
        if self.timer_interceptor:
            self.timer_interceptor.accelerate_timers(page)
            self.timer_interceptor.skip_peliculasgd_timer(page)
            wait_time = AD_WAIT_SECONDS // 5  # Reducir espera 5 veces
        else:
            wait_time = AD_WAIT_SECONDS

        # Esperar
        self.log("STEP6", f"Waiting {wait_time}s for ad timer (accelerated)...")
        elapsed = 0
        while elapsed < wait_time:
            chunk = min(5, wait_time - elapsed)
            time.sleep(chunk)
            elapsed += chunk
            if elapsed < wait_time:
                human_mouse_move(page, steps=1)

    def _step7_return_to_intermediate(self) -> str:
        # Prioridad 1: Ver si el NetworkAnalyzer ya lo capturó
        if self.network_analyzer and self.network_analyzer.captured_links:
            best = self.network_analyzer.get_best_link()
            if best:
                self.log("STEP7", "Found link in network traffic interception!")
                return best

        self.log("STEP7", "Returning to intermediate page...")
        intermediate_page = None
        for p in self.context.pages:
            if p.is_closed():
                continue
            url = p.url.lower()
            if ("peliculasgd" not in url and
                "google" not in url and
                "saboresmexico" not in url and
                "about:blank" not in url):
                intermediate_page = p
                break

        if not intermediate_page:
            for p in self.context.pages:
                if not p.is_closed() and "about:blank" not in p.url:
                    intermediate_page = p
                    break

        if not intermediate_page:
            raise Exception("Could not find intermediate page")

        intermediate_page.bring_to_front()
        intermediate_page.reload(timeout=TIMEOUT_NAV)
        intermediate_page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        random_delay(2.0, 4.0)

        # Buscar link final
        link_selectors = [
            "a[href*='drive.google']",
            "a[href*='mega.nz']",
            "a[href*='mediafire']",
        ]
        for sel in link_selectors:
            el = intermediate_page.query_selector(sel)
            if el:
                href = el.get_attribute("href")
                if href:
                    self.log("STEP7", f"Found: {href[:100]}")
                    return href

        # FALLBACK VISION: Si no encontramos link en el DOM
        if self.vision_resolver:
            self.log("VISION", "DOM search failed - activating Vision fallback...")
            try:
                vision_analysis = self.vision_resolver.analyze_page_sync(intermediate_page)
                if vision_analysis:
                    best_button = self.vision_resolver.find_best_button(vision_analysis)
                    if best_button:
                        # Intentar extraer URL del botón
                        text = best_button.get('text', '').lower()
                        if any(provider in text for provider in ['mega', 'drive', 'mediafire']):
                            if self.vision_resolver.click_button_from_analysis(intermediate_page, best_button):
                                random_delay(1.0, 2.0)
                                # Verificar network analyzer
                                if self.network_analyzer and self.network_analyzer.captured_links:
                                    best = self.network_analyzer.get_best_link()
                                    if best:
                                        self.log("VISION", f"Captured via Vision: {best[:80]}")
                                        return best
            except Exception as vision_error:
                self.log("WARNING", f"Vision fallback failed: {vision_error}")

        intermediate_page.screenshot(path="peliculasgd_final_debug.png")
        self.log("ERROR", "Could not find download link - check peliculasgd_final_debug.png")
        return None

    def _close_unwanted_popups(self, keep_pages: List[Page]):
        for p in self.context.pages:
            if p not in keep_pages and not p.is_closed():
                p.close()

    def _detect_provider(self, url: str) -> str:
        url_lower = url.lower()
        if "drive.google" in url_lower:
            return "drive.google"
        if "mega" in url_lower:
            return "mega"
        if "mediafire" in url_lower:
            return "mediafire"
        return "other"

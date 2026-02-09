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

            # Crear LinkOption para el link final
            link_option = LinkOption(
                url=final_link,
                text="Final link from peliculasgd.net",
                provider=self._detect_provider(final_link),
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

    def _wait_for_new_page(self, trigger_action, timeout=30_000) -> Page:
        """Ejecuta accion que abre nueva pestana y la retorna."""
        with self.context.expect_page(timeout=timeout) as new_page_info:
            trigger_action()
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        return new_page

    def _step1_click_enlaces_publicos(self, page: Page) -> Page:
        self.log("STEP1", "Looking for 'Enlaces Publicos'...")
        selectors = [
            "a:has(img.wp-image-125438)",
            "a:has(img[src*='cxx'])",
            "a:has(img[alt*='enlace' i])",
        ]
        link = None
        for sel in selectors:
            link = page.query_selector(sel)
            if link:
                break
        if not link:
            raise Exception("Enlaces Publicos link not found")
        random_delay(0.5, 1.5)
        new_page = self._wait_for_new_page(lambda: link.click())
        self.log("STEP1", f"Opened: {new_page.url[:60]}...")
        return new_page

    def _step2_click_haz_clic_aqui(self, page: Page) -> Page:
        self.log("STEP2", "Looking for 'Haz clic aqui'...")
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        random_delay(1.0, 3.0)
        selectors = [
            "div.text >> text='Haz clic aquí'",
            "div.text >> text='Haz clic aqui'",
            "text='Haz clic aquí'",
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
        new_page = self._wait_for_new_page(lambda: target.click())
        self.log("STEP2", f"Opened: {new_page.url[:60]}...")
        return new_page

    def _step3_click_continuar(self, page: Page) -> Page:
        self.log("STEP3", "Looking for 'CLIC AQUI PARA CONTINUAR'...")
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        random_delay(1.0, 3.0)
        selectors = [
            "button.button-s:has-text('CLIC')",
            "button.button-s",
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
        new_page = self._wait_for_new_page(lambda: button.click())
        self.log("STEP3", f"Opened Google: {new_page.url[:60]}...")
        return new_page

    def _step4_click_first_google_result(self, page: Page) -> Page:
        self.log("STEP4", "Clicking first Google result...")
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        random_delay(1.5, 3.0)
        selectors = [
            "#search a[href]:not([href*='google'])",
            "#rso a[href]:not([href*='google'])",
        ]
        first_result = None
        for sel in selectors:
            first_result = page.query_selector(sel)
            if first_result:
                break
        if not first_result:
            raise Exception("Google first result not found")
        random_delay(0.5, 1.5)
        new_page = self._wait_for_new_page(lambda: first_result.click())
        self.log("STEP4", f"Landed on: {new_page.url[:60]}...")
        return new_page

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

        # Esperar
        self.log("STEP6", f"Waiting {AD_WAIT_SECONDS}s for ad timer...")
        elapsed = 0
        while elapsed < AD_WAIT_SECONDS:
            chunk = min(10, AD_WAIT_SECONDS - elapsed)
            time.sleep(chunk)
            elapsed += chunk
            if elapsed < AD_WAIT_SECONDS:
                human_mouse_move(page, steps=2)

    def _step7_return_to_intermediate(self) -> str:
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

        intermediate_page.screenshot(path="peliculasgd_final_debug.png")
        return "LINK_NOT_RESOLVED"

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

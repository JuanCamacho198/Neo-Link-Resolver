"""
adapters/hackstore.py - Adaptador para hackstore.mx
Navega en hackstore.mx, busca links segun criterios y los rankea.
"""

from typing import List
from playwright.sync_api import Page
from .base import SiteAdapter
from matcher import LinkOption, LinkMatcher
from config import TIMEOUT_NAV, TIMEOUT_ELEMENT
from human_sim import random_delay, simulate_human_behavior


class HackstoreAdapter(SiteAdapter):
    """
    Adaptador para hackstore.mx
    
    Flujo tipico:
    1. Pagina de pelicula (ej: /peliculas/eragon-2006)
    2. Buscar todos los links de descarga disponibles
    3. Filtrar por criterios (calidad, formato, proveedor)
    4. Retornar el mejor link
    """

    def can_handle(self, url: str) -> bool:
        return "hackstore.mx" in url.lower()

    def name(self) -> str:
        return "Hackstore"

    def resolve(self, url: str) -> LinkOption:
        """
        Navega a la pagina de hackstore y encuentra el mejor link
        segun los criterios.
        """
        self.log("INIT", f"Opening {url[:80]}...")
        
        page = self.context.new_page()
        page.goto(url, timeout=TIMEOUT_NAV)
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        random_delay(1.0, 3.0)

        self.log("INIT", "Movie page loaded. Taking screenshot...")
        page.screenshot(path="hackstore_movie_page.png")

        # Extraer todos los links de descarga disponibles
        raw_links = self._extract_download_links(page)
        self.log("EXTRACT", f"Found {len(raw_links)} download links")

        if not raw_links:
            self.log("ERROR", "No download links found on page")
            page.screenshot(path="hackstore_no_links_debug.png")
            page.close()
            return None

        # Usar el matcher para rankear links
        matcher = LinkMatcher(self.criteria)
        ranked = matcher.parse_and_rank(raw_links)

        # Log de los top 5
        self.log("RANK", "Top 5 links:")
        for i, link in enumerate(ranked[:5], 1):
            self.log("RANK", f"  {i}. {link}")

        best_link = ranked[0]
        self.log("RESULT", f"Best link: {best_link.url[:100]}")

        # Si el mejor link requiere navegacion adicional (ej: acortador),
        # navegar para obtener el link final
        if self._is_shortener(best_link.url):
            self.log("NAV", "Best link is a shortener, resolving...")
            final_url = self._resolve_shortener(page, best_link.url)
            best_link.url = final_url

        page.close()
        return best_link

    def _extract_download_links(self, page: Page) -> List[dict]:
        """
        Extrae todos los links de descarga de la pagina de hackstore.
        
        Hackstore suele tener links organizados en secciones como:
        - Torrent links
        - Direct download links
        - Servidores de almacenamiento
        
        Retorna: [{"url": "...", "text": "..."}, ...]
        """
        links = []

        # Estrategia 1: Buscar links en areas de descarga comunes
        # (adaptar selectores segun la estructura real del sitio)
        download_selectors = [
            "a[href*='torrent']",
            "a[href*='magnet']",
            "a[href*='drive.google']",
            "a[href*='mega']",
            "a[href*='mediafire']",
            "a:has-text('Descargar')",
            "a:has-text('Download')",
            "a:has-text('Torrent')",
            "a:has-text('uTorrent')",
            ".download-link a",
            ".servidor a",
        ]

        for selector in download_selectors:
            elements = page.query_selector_all(selector)
            for el in elements:
                href = el.get_attribute("href")
                if not href or href.startswith("#") or href.startswith("javascript"):
                    continue

                # Obtener el texto del link + texto cercano (para detectar calidad/formato)
                link_text = el.inner_text().strip() if el.inner_text() else ""
                
                # Intentar obtener contexto (div padre que puede tener info de calidad)
                try:
                    parent = el.evaluate("el => el.parentElement?.innerText || ''")
                    link_text = f"{link_text} {parent}"
                except Exception:
                    pass

                links.append({
                    "url": href,
                    "text": link_text[:200],  # Limitar a 200 chars
                })

        # Deduplicar por URL
        seen = set()
        unique_links = []
        for lnk in links:
            if lnk["url"] not in seen:
                seen.add(lnk["url"])
                unique_links.append(lnk)

        return unique_links

    def _is_shortener(self, url: str) -> bool:
        """Retorna True si la URL es un acortador de enlaces."""
        shorteners = ["bit.ly", "tinyurl", "short", "ouo.io", "ow.ly"]
        return any(s in url.lower() for s in shorteners)

    def _resolve_shortener(self, page: Page, shortener_url: str) -> str:
        """
        Navega a traves del acortador y retorna la URL final.
        (Simplificado por ahora, se puede expandir con logica anti-ads)
        """
        try:
            page.goto(shortener_url, timeout=TIMEOUT_NAV)
            page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
            random_delay(2.0, 4.0)
            
            # Esperar redireccion o extraer link final
            final_url = page.url
            self.log("NAV", f"Shortener resolved to: {final_url[:100]}")
            return final_url
        except Exception as e:
            self.log("ERROR", f"Failed to resolve shortener: {e}")
            return shortener_url  # Fallback

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
    Adaptador optimizado para peliculasgd.net
    Usa el contexto persistente y cookies para resolver el link directamente.
    """

    def can_handle(self, url: str) -> bool:
        return "peliculasgd.net" in url.lower() or "peliculasgd.co" in url.lower()

    def name(self) -> str:
        return "PeliculasGD"

    def resolve(self, url: str) -> LinkOption:
        """
        Detección directa del enlace final usando cookies y network interception.
        """
        page = self.context.new_page()

        # Configurar interceptación para capturar links de descarga en el tráfico
        detected_links = []
        def handle_request(request):
            r_url = request.url
            if any(p in r_url for p in ["drive.google.com", "mega.nz", "mediafire.com", "1fichier.com"]):
                if "/view" in r_url or "/file" in r_url or "mega.nz/file" in r_url:
                    detected_links.append(r_url)

        page.on("request", handle_request)

        try:
            self.log("INIT", f"Accediendo a: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_NAV)
            
            # Extraer cookies de la sesión actual
            cookies = self.context.cookies()
            self.log("AUTH", f"Sesión activa con {len(cookies)} cookies detectadas")

            # BUSQUEDA DIRECTA DEL TOKEN 'f' O 'id'
            # En PeliculasGD, el botón de descarga suele tener un link a r.php
            self.log("EXTRACT", "Buscando token de redirección...")
            
            # Intentar encontrarlo en el HTML sin hacer clic
            html = page.content()
            # Patrones comunes en PeliculasGD
            token_match = re.search(r'(r\.php\?f=|l\.php\?o=)([a-zA-Z0-9+/=]+)', html)
            if not token_match:
                token_match = re.search(r'acortame\.site/([a-zA-Z0-9]+)', html)
            
            redir_url = None
            if token_match:
                token = token_match.group(2) if token_match.lastindex >= 2 else token_match.group(1)
                prefix = token_match.group(1)
                # Si es r.php o l.php, construir URL de neworldtravel
                if "php" in prefix:
                    redir_url = f"https://neworldtravel.com/{prefix}{token}"
                else:
                    redir_url = f"https://acortame.site/{token}"
                self.log("EXTRACT", f"URL de redirección encontrada: {redir_url[:60]}...")
            else:
                # Si no está en el HTML, buscar el botón y extraer su href
                btn_selectors = [
                    "a:has(img[src*='cxx'])",
                    "a:has-text('Enlaces Públicos')",
                    "a:has-text('VER ENLACES')",
                    "a:has-text('Descargar')",
                    ".btn-download",
                    "#download_link"
                ]
                
                btn = None
                for sel in btn_selectors:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        break

                if btn:
                    href = btn.get_attribute("href")
                    if href and ("r.php" in href or "acortame" in href or "neworld" in href):
                        redir_url = href
                    else:
                        # Si no tiene href directo o es javascript:void(0), hay que hacer clic
                        self.log("NAV", "Haciendo clic para revelar acortador...")
                        try:
                            # Configurar detección de nueva página (popup)
                            with self.context.expect_page(timeout=10000) as new_page_info:
                                btn.click()
                            new_p = new_page_info.value
                            
                            # Esperar a que la URL del popup se estabilice (no sea about:blank o la home)
                            start_wait = time.time()
                            while time.time() - start_wait < 5:
                                current_p_url = new_p.url
                                if "r.php" in current_p_url or "acortame" in current_p_url or "neworld" in current_p_url:
                                    redir_url = current_p_url
                                    break
                                time.sleep(1)
                            
                            if not redir_url:
                                redir_url = new_p.url
                                
                            new_p.close()
                        except Exception as e:
                            self.log("WARNING", f"Error al clickear/capturar popup: {e}")
                            # Fallback: ver si el link apareció en la página actual
                            new_url = page.url
                            if new_url != url:
                                redir_url = new_url

            if not redir_url:
                # Ultimo recurso: buscar cualquier link que no sea ad en la zona de descarga
                self.log("EXTRACT", "Buscando cualquier link sospechoso de ser acortador...")
                links = page.query_selector_all("a")
                for l in links:
                    h = l.get_attribute("href")
                    if h and ("neworldtravel" in h or "acortame" in h):
                        redir_url = h
                        break

            if not redir_url:
                raise Exception("No se pudo extraer la URL de redirección (acortador)")

            # NAVEGACIÓN DIRECTA AL ACORTADOR CON REFERER
            self.log("NAV", f"Saltando al acortador: {redir_url[:60]}...")
            
            # Si tenemos el ShortenerChainResolver, lo usamos
            if self.shortener_resolver:
                final_link = self.shortener_resolver.resolve(redir_url, page, referer=url)
                if final_link:
                    return self._create_result(final_link, url)

            # Fallback si no hay resolver de acortadores o falló
            page.goto(redir_url, referer=url, timeout=TIMEOUT_NAV)
            
            # Esperar a que el link aparezca en el tráfico o en la página
            start_wait = time.time()
            while time.time() - start_wait < 60:
                if detected_links:
                    return self._create_result(detected_links[0], url)
                
                # Buscar botones de "Obtener Link" o "Ingresa"
                for btn_text in ["Ingresar", "Ingresa", "Link", "Vínculo", "Continuar", "Enlace"]:
                    target = page.query_selector(f"a:has-text('{btn_text}'), button:has-text('{btn_text}')")
                    if target and target.is_visible():
                        opacity = target.evaluate("el => getComputedStyle(el).opacity")
                        if float(opacity) > 0.5:
                            self.log("NAV", f"Botón final detectado: {btn_text}. Clickeando...")
                            target.click()
                            time.sleep(3)
                            break
                
                # Acelerar timers si es posible
                if self.timer_interceptor:
                    self.timer_interceptor.accelerate_timers(page)
                    if "neworldtravel" in page.url or "acortame" in page.url:
                        self.timer_interceptor.skip_peliculasgd_timer(page)
                
                time.sleep(2)

            raise Exception("No se pudo obtener el link final tras la redirección")

        except Exception as e:
            self.log("ERROR", f"Fallo en resolución: {e}")
            page.screenshot(path="logs/peliculasgd_error.png")
            raise e
        finally:
            if not page.is_closed():
                page.close()

    def _create_result(self, final_url: str, original_url: str) -> LinkOption:
        meta = extract_metadata_from_url(original_url)
        provider = "Drive" if "drive.google" in final_url else "Mega" if "mega.nz" in final_url else "1Fichier" if "1fichier" in final_url else "MediaFire"
        
        return LinkOption(
            url=final_url,
            text=f"PeliculasGD - {meta.get('quality', '1080p')}",
            provider=provider,
            quality=meta.get('quality', ""),
            format=meta.get('format', "")
        )

    def log(self, step: str, msg: str):
        print(f"  [PeliculasGD:{step}] {msg}")


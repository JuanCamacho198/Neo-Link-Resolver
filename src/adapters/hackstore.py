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
        
        page = None
        try:
            page = self.context.new_page()
        except Exception as e:
            self.log("ERROR", f"Failed to create new page: {e}")
            return None
        
        try:
            try:
                page.goto(url, timeout=TIMEOUT_NAV)
                page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
            except Exception as e:
                self.log("ERROR", f"Navigation timeout or failed ({url[:60]}): {e}")
                page.screenshot(path="hackstore_nav_error.png")
                return None
            
            random_delay(1.0, 3.0)

            self.log("INIT", "Movie page loaded. Taking screenshot...")
            try:
                page.screenshot(path="hackstore_movie_page.png")
            except Exception as e:
                self.log("WARNING", f"Failed to take screenshot: {e}")

            # Extraer todos los links de descarga disponibles
            try:
                raw_links = self._extract_download_links(page)
                self.log("EXTRACT", f"Found {len(raw_links)} download links")
            except Exception as e:
                self.log("ERROR", f"Failed to extract links: {e}")
                return None

            if not raw_links:
                self.log("ERROR", "No download links found on page")
                try:
                    page.screenshot(path="hackstore_no_links_debug.png")
                except:
                    pass
                return None

            # Usar el matcher para rankear links
            try:
                matcher = LinkMatcher(self.criteria)
                ranked = matcher.parse_and_rank(raw_links)
            except Exception as e:
                self.log("ERROR", f"Failed to rank links: {e}")
                return None

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
                try:
                    final_url = self._resolve_shortener(page, best_link.url)
                    best_link.url = final_url
                except Exception as e:
                    self.log("WARNING", f"Failed to resolve shortener: {e}")
                    # Continuar con URL original si falla

            return best_link
        
        except Exception as e:
            self.log("ERROR", f"Unexpected error in resolve: {e}")
            return None
        
        finally:
            # Cleanup: Always close page
            if page:
                try:
                    page.close()
                except Exception as e:
                    self.log("WARNING", f"Error closing page: {e}")

     def _extract_download_links(self, page: Page) -> List[dict]:
          """
          Extrae los links de descarga de hackstore de forma interactiva.
          
          Hackstore usa un sistema dinámico donde:
          1. Se muestran headings con calidades: "WEB-DL 1080p", "1080p", "720p"
          2. Al hacer click en el heading, se expanden los proveedores disponibles
          3. Cada proveedor tiene un botón "Descargar" que redirige a la URL final
          
          Flujo:
          - Buscar todos los headings h3 con calidad
          - Para cada heading, hacer click para expandir
          - Esperar a que aparezcan los botones de proveedor
          - Hacer click en cada botón de proveedor (preferentemente utorrent, mega, mediafire)
          - Capturar la URL a la que redirige
          
          Retorna: [{"url": "...", "text": "..."}, ...]
          """
          links = []
          
          try:
              # Esperar a que los elementos de descarga carguen
              try:
                  page.wait_for_selector("h3", timeout=TIMEOUT_ELEMENT * 1000)
              except Exception as e:
                  self.log("WARNING", f"Timeout waiting for h3 elements: {e}")
              
              # Obtener el HTML completo como fallback
              html_content = page.content()
              
              # Patrones de proveedores conocidos (en orden de preferencia)
              providers_preferred = [
                  "utorrent",
                  "mega",
                  "mediafire",
                  "drive.google",
                  "dropbox"
              ]
              
              providers_all = [
                  "utorrent.com",
                  "mega.nz",
                  "www.mediafire.com",
                  "megaup.net",
                  "1fichier.com",
                  "ranoz.gg",
                  "drive.google.com",
                  "dropbox.com",
                  "gofile.io",
                  "mediafire",
                  "mega",
                  "dropbox",
                  "google drive"
              ]
              
              # Buscar headings de calidad
              try:
                  headings = page.query_selector_all("h3")
              except Exception as e:
                  self.log("WARNING", f"Failed to query h3 selectors: {e}")
                  headings = []
              
              qualities_found = []
              
              for heading in headings:
                  try:
                      text = heading.inner_text().strip()
                      if any(q in text.lower() for q in ["1080p", "720p", "480p", "dvdrip", "web-dl", "bluray", "remux", "1080", "720", "480"]):
                          qualities_found.append((text, heading))
                          self.log("EXTRACT", f"Found quality section: {text}")
                  except Exception as e:
                      self.log("WARNING", f"Error reading heading text: {e}")
                      continue
              
              if not qualities_found:
                  self.log("EXTRACT", "No quality sections found, using fallback HTML search")
                  return self._extract_links_fallback(html_content, providers_all)
              
              self.log("EXTRACT", f"Found {len(qualities_found)} quality sections, processing interactively...")
              
              # Procesar cada calidad de forma interactiva
              for quality_text, heading_element in qualities_found:
                  self.log("EXTRACT", f"Processing quality: {quality_text}")
                  
                  try:
                      # Hacer scroll hasta el elemento si es necesario
                      try:
                          heading_element.scroll_into_view_if_needed()
                      except Exception as e:
                          self.log("WARNING", f"Failed to scroll into view: {e}")
                      
                      random_delay(0.3, 0.7)
                      
                      # Click en el heading para expandir
                      try:
                          heading_element.click()
                      except Exception as e:
                          self.log("WARNING", f"Failed to click heading: {e}")
                          continue
                      
                      random_delay(0.5, 1.5)
                      self.log("EXTRACT", f"  Clicked on {quality_text}, waiting for providers to appear...")
                      
                      # Esperar a que aparezcan los botones de descarga
                      # Los botones típicamente aparecen como <a>, <button>, o elementos con clase "download", "descargar"
                      try:
                          # Intentar esperar a que aparezcan elementos de descarga
                          page.wait_for_selector("a[href*='descargar'], button:has-text('Descargar'), .btn-descargar", timeout=3000)
                      except:
                          self.log("EXTRACT", "  No download button selector found, searching for provider links...")
                      
                      # Buscar botones de proveedor cerca del heading expandido
                      # Generalmente están en el siguiente párrafo o div
                      try:
                          provider_elements = self._find_provider_buttons_after_heading(page, heading_element)
                      except Exception as e:
                          self.log("WARNING", f"Failed to find provider buttons: {e}")
                          provider_elements = []
                      
                      self.log("EXTRACT", f"  Found {len(provider_elements)} provider buttons for {quality_text}")
                      
                      for provider_button in provider_elements:
                          try:
                              provider_text = provider_button.inner_text().strip()
                              
                              # Identificar el proveedor
                              provider_name = self._identify_provider(provider_text, providers_all)
                              
                              if not provider_name:
                                  self.log("EXTRACT", f"    Skipping unknown provider: {provider_text}")
                                  continue
                              
                              self.log("EXTRACT", f"    Clicking provider: {provider_name}")
                              
                              # Hacer click en el botón del proveedor
                              # Usar una estrategia de seguimiento de respuesta para capturar la URL
                              try:
                                  page.on("response", lambda response: self._capture_redirect_url(response, quality_text, provider_name, links))
                              except Exception as e:
                                  self.log("WARNING", f"Failed to register response listener: {e}")
                              
                              try:
                                  provider_button.click()
                              except Exception as e:
                                  self.log("WARNING", f"Failed to click provider button: {e}")
                                  continue
                              
                              random_delay(1.0, 2.0)
                              
                              # Intentar obtener la URL actual (podría haber sido redirigida)
                              try:
                                  current_url = page.url
                                  if current_url and not current_url.startswith("https://hackstore.mx"):
                                      # La página fue redirigida a un destino real
                                      links.append({
                                          "url": current_url,
                                          "text": f"{quality_text} - {provider_name}"
                                      })
                                      self.log("EXTRACT", f"    Captured URL: {current_url[:80]}")
                              except Exception as e:
                                  self.log("WARNING", f"Failed to get current URL: {e}")
                              
                              # Volver a la página original
                              try:
                                  page.go_back()
                                  random_delay(1.0, 2.0)
                              except Exception as e:
                                  self.log("WARNING", f"Failed to go back: {e}")
                              
                          except Exception as e:
                              self.log("WARNING", f"    Error processing provider button: {e}")
                              continue
                  
                  except Exception as e:
                      self.log("WARNING", f"Error processing quality {quality_text}: {e}")
                      continue
              
              # Si no encontramos links interactivamente, usar fallback
              if not links:
                  self.log("EXTRACT", "No links found interactively, using fallback HTML search...")
                  links = self._extract_links_fallback(html_content, providers_all)
          
          except Exception as e:
              self.log("ERROR", f"Exception in _extract_download_links: {e}")
              # Fallback a búsqueda HTML simple
              try:
                  html = page.content()
                  links = self._extract_links_fallback(html, providers_all)
              except Exception as fallback_e:
                  self.log("ERROR", f"Fallback also failed: {fallback_e}")
          
          # Deduplicar
          seen = set()
          unique_links = []
          for link in links:
              if link.get("url") and link["url"] not in seen:
                  seen.add(link["url"])
                  unique_links.append(link)
          
          return unique_links
     
    def _find_provider_buttons_after_heading(self, page: Page, heading_element) -> List:
        """
        Encuentra los botones de proveedor que aparecen después de hacer click en un heading.
        """
        try:
            # Buscar el contenedor padre del heading
            parent = heading_element.evaluate_handle("el => el.parentElement")
            
            # Buscar todos los botones/links dentro del padre o hermanos siguientes
            # Típicamente están en <a>, <button>, o divs con clase específica
            buttons = []
            
            # Estrategia 1: Buscar en el siguiente elemento hermano
            next_sibling = heading_element.evaluate_handle("el => el.nextElementSibling")
            if next_sibling:
                buttons_in_sibling = next_sibling.query_selector_all("a, button, [role='button']")
                buttons.extend(buttons_in_sibling)
            
            # Estrategia 2: Buscar en los siguientes elementos hermanos (hasta 3)
            current = heading_element
            for _ in range(3):
                next_elem = current.evaluate_handle("el => el.nextElementSibling")
                if next_elem:
                    new_buttons = next_elem.query_selector_all("a, button, [role='button']")
                    buttons.extend(new_buttons)
                    current = next_elem
            
            # Estrategia 3: Buscar dentro del padre directo
            parent_buttons = parent.query_selector_all("a, button, [role='button']")
            buttons.extend(parent_buttons)
            
            # Filtrar botones relevantes (que contengan nombre de proveedor o texto de descarga)
            relevant_buttons = []
            for btn in buttons:
                try:
                    text = btn.inner_text().strip().lower()
                    if any(word in text for word in ["descargar", "download", "mega", "mediafire", "utorrent", "drive", "dropbox"]):
                        relevant_buttons.append(btn)
                except:
                    continue
            
            return relevant_buttons if relevant_buttons else buttons
        
        except Exception as e:
            self.log("ERROR", f"Error finding provider buttons: {e}")
            return []
    
    def _identify_provider(self, text: str, providers_list: List[str]) -> str:
        """
        Identifica el nombre del proveedor a partir del texto del botón.
        """
        text_lower = text.lower()
        
        for provider in providers_list:
            provider_lower = provider.lower()
            if provider_lower in text_lower:
                # Extraer el nombre base
                short_name = provider.split('.')[0].lower()
                return short_name
        
        # Fallback: si la palabra contiene "descargar", extrae el resto
        if "descargar" in text_lower:
            return text.replace("Descargar", "").replace("descargar", "").strip()
        
        return text
    
    def _capture_redirect_url(self, response, quality: str, provider: str, links: List[dict]):
        """
        Callback para capturar URLs de redirección.
        """
        try:
            if response.status == 302 or response.status == 301:
                redirect_url = response.headers.get("location")
                if redirect_url and "hackstore.mx" not in redirect_url.lower():
                    links.append({
                        "url": redirect_url,
                        "text": f"{quality} - {provider}"
                    })
                    self.log("EXTRACT", f"Captured redirect: {redirect_url[:80]}")
        except:
            pass
    
    def _extract_links_fallback(self, html_content: str, providers: List[str]) -> List[dict]:
        """
        Fallback: extrae links basándose en búsqueda en el HTML.
        Crea links representativos basados en calidades y proveedores encontrados.
        """
        links = []
        
        try:
            # Buscar menciones de proveedores en el HTML
            found_providers = []
            for provider in providers:
                if provider.lower() in html_content.lower():
                    found_providers.append(provider)
                    self.log("EXTRACT", f"Found provider in HTML: {provider}")
            
            # Crear links representativos (para ranking)
            quality_patterns = ["1080p", "720p", "480p", "web-dl", "bluray"]
            found_qualities = []
            
            for quality in quality_patterns:
                if quality.lower() in html_content.lower():
                    found_qualities.append(quality)
                    self.log("EXTRACT", f"Found quality in HTML: {quality}")
            
            if not found_qualities:
                found_qualities = ["1080p"]
            
            if not found_providers:
                found_providers = ["mediafire"]
            
            # Generar links representativos
            for quality in found_qualities:
                for provider in found_providers:
                    links.append({
                        "url": f"https://hackstore.mx/download/{quality.replace(' ', '-')}/{provider.split('.')[0]}",
                        "text": f"{quality} - {provider}"
                    })
        
        except Exception as e:
            self.log("ERROR", f"Error in fallback extraction: {e}")
        
        return links

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

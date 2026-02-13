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

    def detect_providers(self, url: str) -> List[str]:
        """
        Detecta los proveedores disponibles en una página de película.
        
        Retorna: ["mediafire", "mega", "utorrent", ...]
        """
        self.log("INIT", f"Detecting providers from {url[:80]}...")
        
        page = None
        try:
            page = self.context.new_page()
        except Exception as e:
            self.log("ERROR", f"Failed to create new page: {e}")
            return []
        
        providers_found = set()
        
        try:
            try:
                page.goto(url, timeout=TIMEOUT_NAV)
                page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
            except Exception as e:
                self.log("ERROR", f"Navigation timeout: {e}")
                return []
            
            random_delay(1.0, 2.0)
            
            # Obtener el HTML completo
            html_content = page.content()
            
            # Patrones de proveedores (actualizar si es necesario)
            provider_patterns = {
                r'(?:href|link)["\']?[^"\']*(?:mediafire|www\.mediafire)': 'MediaFire',
                r'(?:href|link)["\']?[^"\']*(?:mega\.nz|mega\.io|mega\.co\.nz)': 'MEGA',
                r'(?:href|link)["\']?[^"\']*(?:drive\.google|google\.drive|accounts\.google)': 'Google Drive',
                r'(?:href|link)["\']?[^"\']*dropbox': 'Dropbox',
                r'(?:href|link)["\']?[^"\']*utorrent': 'uTorrent',
                r'(?:href|link)["\']?[^"\']*1fichier': '1Fichier',
                r'(?:href|link)["\']?[^"\']*gofile': 'GoFile',
            }
            
            import re
            html_lower = html_content.lower()
            
            # Buscar proveedores en el HTML
            for pattern, provider_name in provider_patterns.items():
                if re.search(pattern, html_lower):
                    providers_found.add(provider_name)
                    self.log("EXTRACT", f"Found provider: {provider_name}")
            
            # Si no encontramos nada, buscar en texto
            if not providers_found:
                common_providers = ['mediafire', 'mega', 'drive', 'dropbox', 'utorrent', '1fichier', 'gofile']
                for provider in common_providers:
                    if provider in html_lower:
                        # Capitalizar correctamente
                        if provider == 'mediafire':
                            providers_found.add('MediaFire')
                        elif provider == 'mega':
                            providers_found.add('MEGA')
                        elif provider == 'drive':
                            providers_found.add('Google Drive')
                        elif provider == 'dropbox':
                            providers_found.add('Dropbox')
                        elif provider == 'utorrent':
                            providers_found.add('uTorrent')
                        elif provider == '1fichier':
                            providers_found.add('1Fichier')
                        elif provider == 'gofile':
                            providers_found.add('GoFile')
                        self.log("EXTRACT", f"Found provider (HTML search): {provider}")
        
        except Exception as e:
            self.log("ERROR", f"Error detecting providers: {e}")
        
        finally:
            if page:
                try:
                    page.close()
                except Exception as e:
                    self.log("WARNING", f"Error closing page: {e}")
        
        # Retornar lista ordenada (proveedores preferidos primero)
        preferred_order = ['MEGA', 'MediaFire', 'Google Drive', 'uTorrent', 'Dropbox']
        providers_ordered = [p for p in preferred_order if p in providers_found]
        providers_ordered.extend(sorted(providers_found - set(preferred_order)))
        
        return providers_ordered if providers_ordered else []
    
    def resolve(self, url: str) -> LinkOption:
        """
        Navega a la pagina de hackstore y encuentra el mejor link
        segun los criterios.
        """
        self.log("INIT", f"Opening {url[:80]}...")
        
        page = None
        try:
            page = self.context.new_page()
            self.page = page # Almacenar referencia para métodos internos
            
            # Activar Network Interceptor
            if self.network_analyzer:
                self.network_analyzer.setup_network_interception(page, block_ads=True)
                
        except Exception as e:
            self.log("ERROR", f"Failed to create new page: {e}")
            return None
        
        try:
            # Reintento para la navegación inicial si falla por abort
            max_nav_retries = 2
            for nav_attempt in range(max_nav_retries):
                try:
                    page.goto(url, timeout=TIMEOUT_NAV)
                    page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
                    break # Éxito
                except Exception as e:
                    if "ERR_ABORTED" in str(e) and nav_attempt < max_nav_retries - 1:
                        self.log("NAV", f"Retrying navigation due to aborted frame (attempt {nav_attempt+2})...")
                        page.wait_for_timeout(1000)
                        continue
                    self.log("ERROR", f"Navigation timeout or failed ({url[:60]}): {e}")
                    try:
                        page.screenshot(path="hackstore_nav_error.png")
                    except:
                        pass
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
              
              # Si no hay h3, intentar con otras etiquetas
              if not headings or len(headings) == 0:
                  self.log("EXTRACT", "No h3 found, trying h2, h4, div.quality, .download-section...")
                  try:
                      alternative_selectors = ["h2", "h4", "div[class*='quality']", "div[class*='download']", ".quality-section"]
                      for selector in alternative_selectors:
                          headings = page.query_selector_all(selector)
                          if headings and len(headings) > 0:
                              self.log("EXTRACT", f"Found {len(headings)} elements with selector: {selector}")
                              break
                  except Exception as e:
                      self.log("WARNING", f"Alternative selectors also failed: {e}")
                      headings = []
              
              qualities_found = []
              
              for heading in headings:
                  try:
                      text = heading.inner_text().strip()
                      # Patrones más amplios para detectar calidades
                      quality_patterns = [
                          "2160p", "4k", "1080p", "720p", "480p", "360p",
                          "1080", "720", "480",
                          "dvdrip", "web-dl", "webdl", "bluray", "blu-ray", "brrip", "bdrip",
                          "remux", "webrip", "hdtv", "hdrip"
                      ]
                      if any(q in text.lower() for q in quality_patterns):
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
                              try:
                                  provider_button.click()
                              except Exception as e:
                                  self.log("WARNING", f"Failed to click provider button: {e}")
                                  continue
                              
                              random_delay(1.5, 3.0)
                              
                              # Verificar si el NetworkAnalyzer capturó algo
                              if self.network_analyzer and self.network_analyzer.captured_links:
                                  for captured in self.network_analyzer.captured_links:
                                      if self.network_analyzer.is_download_url(captured['url']):
                                          links.append({
                                              "url": captured['url'],
                                              "text": f"{quality_text} {provider_name}",
                                              "provider": provider_name,
                                              "quality": quality_text
                                              # Score will be calculated later
                                          })
                                          # Limpiar capturas una vez procesadas para evitar duplicados en la siguiente calidad
                                          self.network_analyzer.captured_links = []
                                          break
                              
                              # Fallback: Intentar obtener la URL actual (podría haber sido redirigida)
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
              
              # FALLBACK VISION: Si aún no hay links Y vision está disponible
              if not links and self.vision_resolver:
                  self.log("VISION", "Activating Vision fallback to identify download buttons...")
                  try:
                      vision_analysis = self.vision_resolver.analyze_page_sync(page)
                      if vision_analysis:
                          best_button = self.vision_resolver.find_best_button(vision_analysis)
                          if best_button:
                              # Intentar click en el botón identificado por Vision
                              if self.vision_resolver.click_button_from_analysis(page, best_button):
                                  random_delay(2.0, 4.0)
                                  # Verificar si se capturó algo en la red
                                  if self.network_analyzer and self.network_analyzer.captured_links:
                                      for captured in self.network_analyzer.captured_links:
                                          links.append({
                                              "url": captured['url'],
                                              "text": best_button.get('text', 'Vision-detected button')
                                          })
                                  else:
                                      # Verificar URL actual
                                      current_url = page.url
                                      if current_url and "hackstore.mx" not in current_url:
                                          links.append({
                                              "url": current_url,
                                              "text": best_button.get('text', 'Vision-detected button')
                                          })
                  except Exception as vision_error:
                      self.log("WARNING", f"Vision fallback failed: {vision_error}")
          
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
            # Buscar todos los botones/links dentro de la página
            buttons = []
            
            # Use evaluate to get button elements safely
            button_elements = page.query_selector_all("a[href], button, [role='button']")
            
            if button_elements:
                buttons.extend(button_elements)
            
            # Filtrar botones relevantes (que contengan nombre de proveedor o texto de descarga)
            relevant_buttons = []
            for btn in buttons:
                try:
                    text = btn.inner_text().strip().lower()
                    is_relevant_text = any(word in text for word in ["descargar", "download", "mega", "mediafire", "utorrent", "drive", "dropbox"])
                    
                    if not is_relevant_text:
                        continue

                    # INTEGRACION DOM ANALYZER
                    if self.dom_analyzer:
                        features = self.dom_analyzer.get_element_features(btn)
                        if features:
                            score = self.dom_analyzer.calculate_realness_score(features)
                            if score < 0.4:  # Umbral para filtrar falsos
                                self.log("DOM", f"Filtered weak button (score {score:.2f}): {text[:20]}")
                                continue
                            else:
                                self.log("DOM", f"Kept strong button (score {score:.2f}): {text[:20]}")
                    
                    relevant_buttons.append(btn)
                except Exception as e:
                    self.log("WARNING", f"Error analyzing button: {e}")
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
        Fallback: extrae links basándose en búsqueda directa en el DOM.
        Busca cualquier link que parezca ser un acortador o link de descarga.
        """
        candidates = []
        
        try:
            # Intentar expandir todo antes de buscar
            self.log("EXTRACT", "Attempting to expand all 'Ver Enlaces' buttons...")
            expand_selectors = [
                "button:has-text('VER ENLACES')", 
                "button:has-text('Ver Enlaces')",
                ".btn-enlaces",
                "#ver-enlaces"
            ]
            
            for selector in expand_selectors:
                try:
                    buttons = self.page.query_selector_all(selector)
                    for btn in buttons:
                        if btn.is_visible():
                            btn.click()
                            random_delay(0.5, 1.0)
                except:
                    continue

            # Buscar todos los links en la página
            self.log("EXTRACT", "Searching DOM for potential download/shortener links...")
            links_data = self.page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.innerText.trim(),
                    href: a.href,
                    parentText: a.parentElement ? a.parentElement.innerText.trim() : ""
                }));
            }""")
            
            for link in links_data:
                url = link['href']
                text = link['text'].lower()
                parent_text = link['parentText'].lower()
                
                # Clasificar link
                is_valid = False
                source = "DOM Search"
                
                # Heurística: Dominio de descarga directa o acortador conocido
                if self.network_analyzer:
                    if self.network_analyzer.is_download_url(url) or self.network_analyzer.is_shortener_url(url):
                        is_valid = True
                
                # Heurística: Patrones de URL de Hackstore para links
                if "/links/" in url or "/link/" in url or "acortame.site" in url:
                    is_valid = True
                
                if is_valid:
                    # Intentar inferir calidad del texto circundante
                    quality = "1080p" # Default
                    for q in ["2160p", "4k", "1080p", "720p", "480p", "web-dl", "bluray"]:
                        if q in text or q in parent_text or q in url.lower():
                            quality = q
                            break
                    
                    # Intentar inferir proveedor
                    provider = "other"
                    for p in providers:
                        p_clean = p.replace(".com", "").replace(".nz", "").lower()
                        if p_clean in url.lower() or p_clean in text or p_clean in parent_text:
                            provider = p
                            break
                    
                    candidates.append({
                        'url': url,
                        'quality': quality,
                        'provider': provider,
                        'format': "WEB-DL",
                        'score': 50 # Score base medio
                    })
            
            self.log("EXTRACT", f"Fallback found {len(candidates)} potential links")
        
        except Exception as e:
            self.log("ERROR", f"Error in fallback extraction: {e}")
        
        return candidates

    def _is_shortener(self, url: str) -> bool:
        """Retorna True si la URL es un acortador de enlaces."""
        if self.network_analyzer:
            return self.network_analyzer.is_shortener_url(url)
        
        # Fallback simple
        shorteners = ["bit.ly", "tinyurl", "short", "ouo.io", "ow.ly", "acortame.site", "acortalo.link"]
        return any(s in url.lower() for s in shorteners)

    def _resolve_shortener(self, page: Page, shortener_url: str) -> str:
        """
        Navega a traves del acortador y retorna la URL final.
        Usa ShortenerChainResolver para seguir cadenas complejas.
        """
        if self.shortener_resolver:
            resolved = self.shortener_resolver.resolve(shortener_url, page)
            if resolved:
                return resolved
                
        # Fallback a la implementación anterior si no hay resolver o falla
        try:
            self.log("NAV", f"Simplified resolution fallback for: {shortener_url[:50]}")
            page.goto(shortener_url, timeout=TIMEOUT_NAV)
            page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
            
            # Esperar redireccion o extraer link final
            final_url = page.url
            return final_url
        except Exception as e:
            self.log("ERROR", f"Failed to resolve shortener: {e}")
            return shortener_url

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

            # NUEVO: Cerrar posible splash screen / disclaimer
            try:
                self.log("INIT", "Checking for splash screen...")
                splash_btn = page.query_selector("a:has-text('Continuar'), button:has-text('Continuar')")
                if splash_btn and splash_btn.is_visible():
                    self.log("INIT", "Closing splash screen (Continuar)...")
                    splash_btn.click()
                    page.wait_for_timeout(1000)
            except: pass

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
        """
        links = []
        providers_all = [
            "utorrent.com", "mega.nz", "www.mediafire.com", "megaup.net", 
            "1fichier.com", "ranoz.gg", "drive.google.com", "dropbox.com", 
            "gofile.io", "mediafire", "mega", "dropbox", "google drive"
        ]
        
        try:
            from human_sim import simulate_human_behavior
            # Esperar a que los elementos de descarga carguen
            self.log("EXTRACT", "Waiting for visible quality text (1080p, 720p, Bluray)...")
            
            # Interactuar un poco para despertar el renderizado reactivo
            simulate_human_behavior(page, intensity="light")
            
            # Intentar encontrar texto de calidad VISIBLE (excluyendo scripts)
            quality_loaded = False
            for i in range(20): # Aumentar a 20 segundos
                try:
                    # Intentar scroll para activar carga perezosa
                    if i % 5 == 0:
                        page.mouse.wheel(0, 500)
                    
                    body_text = page.inner_text("body").lower()
                    if any(q in body_text for q in ["1080p", "720p", "bluray", "dvdrip", "calidad"]):
                        self.log("EXTRACT", f"Quality text detected in visible body after {i}s!")
                        quality_loaded = True
                        break
                except:
                    pass
                
                page.wait_for_timeout(1000)

            if not quality_loaded:
                # FALLBACK EXTREMO: Si no hay texto visible, buscar en TODO el HTML
                html_content = page.content().lower()
                if any(q in html_content for q in ["1080p", "720p", "bluray", "dvdrip"]):
                    self.log("WARNING", "Quality text found in HTML/Scripts but NOT visible in body. Attempting forced extraction...")
                    quality_loaded = True
                else:
                    self.log("ERROR", "No quality text found anywhere. Page might be restricted.")
                    page.screenshot(path="logs/hackstore_blocked_debug.png")
                    return []
            self.log("DEBUG", "Searching for quality elements via JS...")
            tag_info = page.evaluate("""() => {
                const results = [];
                const searchTerms = ['1080p', '720p', 'bluray', 'dvdrip'];
                document.querySelectorAll('*').forEach(el => {
                    const text = el.innerText || "";
                    if (searchTerms.some(q => text.toLowerCase().includes(q)) && el.children.length === 0) {
                        results.push({ tag: el.tagName, text: text.substring(0, 30), classes: el.className });
                    }
                });
                return results;
            }""")
            for info in tag_info:
                self.log("DEBUG", f"Found quality-like tag: <{info['tag']}> class='{info['classes']}' text='{info['text']}'")

            # Buscar cabeceras que contengan calidad
            # Ampliar aún más la búsqueda a CUALQUIER etiqueta que sea "hoja" (sin hijos) o tenga texto corto
            headings = page.query_selector_all("h1, h2, h3, h4, h5, h6, b, strong, .font-bold, .text-xl, div:not(:has(*))")
            self.log("EXTRACT", f"Total potential elements found: {len(headings)}")
            
            relevant_headings = []
            for h in headings:
                try:
                    text = h.text_content().strip()
                    # Filtro de longitud para evitar parrafos gigantes
                    if len(text) < 50 and any(q in text.lower() for q in ["1080p", "720p", "4k", "dvdrip", "hd", "web-dl", "bluray"]):
                        relevant_headings.append(h)
                except:
                    continue
            
            if not relevant_headings:
                self.log("ERROR", "No relevant quality headings found among potential list. Using direct button scan.")
                # Si fallan los headings, intentamos buscar TODOS los botones de descarga
                return self._extract_links_direct_scan(page, providers_all)

            self.log("EXTRACT", f"Found {len(relevant_headings)} relevant quality headings.")
            original_url = page.url

            # Eliminar duplicados de headings por texto para no procesar 2 veces lo mismo
            unique_headings = []
            seen_texts = set()
            for h in relevant_headings:
                txt = h.text_content().strip().lower()
                if txt not in seen_texts:
                    seen_texts.add(txt)
                    unique_headings.append(h)
            
            # NUEVA ESTRATEGIA: Hunter de botones de descarga
            self.log("EXTRACT", "Searching for all 'Descargar' buttons in page...")
            
            # Buscar todos los botones que digan Descargar/Download
            all_buttons = page.query_selector_all("button, a")
            download_candidates = []
            
            for btn in all_buttons:
                try:
                    if not btn.is_visible(): continue
                    text = btn.inner_text().strip().upper()
                    if "DESCARGAR" in text or "DOWNLOAD" in text or "VER ENLACES" in text:
                        download_candidates.append(btn)
                except: continue
                
            self.log("EXTRACT", f"Found {len(download_candidates)} potential download/expand buttons.")
            
            # Primero expandir todos los "VER ENLACES"
            for btn in download_candidates:
                try:
                    btn_text = btn.inner_text().upper()
                    if "VER ENLACES" not in btn_text: continue
                    
                    self.log("EXTRACT", f"Clicking expander: {btn_text[:20]}...")
                    try:
                        btn.click(timeout=3000)
                    except Exception as e:
                        if "intercepts pointer events" in str(e).lower():
                            self.log("EXTRACT", "Expander intercepted. Clearing overlays...")
                            page.evaluate("""() => {
                                document.querySelectorAll('.fixed, .backdrop-blur-sm, [class*="overlay"]').forEach(el => el.remove());
                            }""")
                            btn.click(force=True)
                        else:
                            btn.click(force=True)
                    page.wait_for_timeout(500)
                except: continue
            
            # Ahora buscar los botones de descarga REALES (los que aparecen tras expandir)
            self.log("EXTRACT", "Searching for provider-specific download buttons...")
            page.wait_for_timeout(2000)
            all_elements = page.query_selector_all("button, a")
            
            for el in all_elements:
                try:
                    el_text = (el.text_content() or "").strip().upper()
                    
                    # Ignorar expansores (los que ya clickamos) y textos vacíos
                    if not el_text or "VER ENLACES" in el_text: continue
                    
                    # Criterio más estricto
                    providers_keywords = ["MEGA", "MEDIAFIRE", "UTORRENT", "FICHIER", "DRIVE", "UPTOBOX", "UPSTREAM", "STREAM"]
                    is_download = "DESCARGAR" in el_text or "DOWNLOAD" in el_text or any(p in el_text for p in providers_keywords)
                    
                    if not is_download:
                        continue
                        
                    if len(el_text) > 30: # Un botón real de proveedor no suele ser tan largo
                        continue
                    
                    self.log("DEBUG", f"Found valid download button: '{el_text}'")

                    # Obtener contexto (proveedor y calidad)
                    # Subir un par de niveles para ver dónde está el botón encerrado
                    container = page.evaluate_handle("el => el.closest('.flex, .grid, .row, tr, div[class*=\"link\"]') || el.parentElement", el)
                    context_text = container.as_element().inner_text().lower() if container else ""
                    
                    provider = self._identify_provider(el_text, providers_all) # Preferir el texto del botón mismo
                    if provider == el_text.lower(): # Si no identificó un proveedor conocido
                         provider = self._identify_provider(context_text, providers_all)

                    # Identificar calidad subiendo más niveles
                    quality = page.evaluate("""(el) => {
                        let curr = el;
                        for (let i = 0; i < 25; i++) {
                            if (!curr) break;
                            let text = curr.innerText || "";
                            let q = text.match(/(1080p|720p|4k|dvdrip|bluray|web-dl|dvd-rip)/i);
                            if (q) return q[0].toUpperCase();
                            curr = curr.previousElementSibling || curr.parentElement;
                        }
                        return "Unknown";
                    }""", el)
                    
                    links.append({
                        "url": "btn_click",
                        "quality": quality,
                        "provider": provider,
                        "handle": el,
                        "name": f"{provider} ({quality})"
                    })
                except: continue

            if not links:
                self.log("ERROR", "No download buttons identified after expansion.")
                return []

            self.log("EXTRACT", f"Identified {len(links)} interactive download links.")

            unique_final_links = []
            for link in links:
                btn = link["handle"]
                item_name = link.get("name", "Unknown Item")
                
                self.log("EXTRACT", f"Attempting to resolve {item_name}...")
                try:
                    target_page = None
                    # Intentar hasta 2 veces (a veces el primer click abre un popup bloqueado y el segundo el link)
                    for attempt in range(2):
                        try:
                            with page.context.expect_page(timeout=7000) as new_page_info:
                                # Asegurar que el botón es visible y darle click
                                btn.scroll_into_view_if_needed()
                                try:
                                    btn.click(timeout=4000)
                                except:
                                    # Si falla el click normal, limpiar overlays y forzar
                                    page.evaluate("() => document.querySelectorAll('.fixed, .backdrop-blur-sm').forEach(el => el.remove())")
                                    btn.click(force=True)
                            
                            target_page = new_page_info.value
                            break # Éxito
                        except:
                            self.log("DEBUG", f"Attempt {attempt+1} failed to open new page. Retrying click...")
                            page.wait_for_timeout(1000)
                    
                    if not target_page:
                        self.log("WARNING", f"Could not trigger new tab for {item_name}")
                        continue

                    # Procesar la nueva página
                    target_page.wait_for_load_state("domcontentloaded", timeout=15000)
                    final_url = target_page.url
                    
                    self.log("NAV", f"New tab opened: {final_url[:60]}")

                    if self.shortener_resolver and self.shortener_resolver.is_shortener(final_url):
                        self.log("NAV", f"    Resolving shortener for {item_name}...")
                        resolved = self.shortener_resolver.resolve(final_url, target_page)
                        if resolved:
                            final_url = resolved
                    
                    if final_url and "hackstore.mx" not in final_url:
                        unique_final_links.append({
                            "url": final_url,
                            "text": item_name,
                            "quality": link["quality"],
                            "provider": link["provider"]
                        })
                        self.log("SUCCESS", f"    Resolved: {final_url[:60]}")
                    
                    target_page.close()
                    # Si ya conseguimos uno de buena calidad, podemos parar o seguir
                    # Por ahora seguimos para sacar todos los posibles
                except Exception as e:
                    self.log("WARNING", f"    Failed to process {item_name}: {e}")

            return unique_final_links

        except Exception as e:
            self.log("ERROR", f"Error in _extract_download_links: {e}")
            return []
     
    def _extract_links_direct_scan(self, page: Page, providers: List[str]) -> List[dict]:
        """
        Escaneo directo de botones de descarga sin depender de headings.
        """
        self.log("EXTRACT", "Executing direct button scan fallback...")
        links = []
        try:
            # Buscar todos los botones o links que digan descargar
            buttons = page.query_selector_all("button, a")
            for btn in buttons:
                try:
                    text = btn.inner_text().upper()
                    if "DESCARGAR" in text or "DOWNLOAD" in text:
                        # Intentar encontrar calidad cerca (padre o abuelo)
                        parent = page.evaluate_handle("el => el.closest('.flex-1') || el.parentElement.parentElement", btn)
                        quality = "Unknown"
                        if parent:
                            p_text = parent.as_element().inner_text()
                            for q in ["1080p", "720p", "4k", "dvdrip"]:
                                if q in p_text.lower():
                                    quality = q
                                    break
                        
                        links.append({
                            "url": "direct_scan", # Marcador
                            "text": f"{quality} Download",
                            "quality": quality,
                            "provider": "unknown",
                            "handle": btn
                        })
                except: continue
        except Exception as e:
            self.log("ERROR", f"Error in direct scan: {e}")
        return links

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

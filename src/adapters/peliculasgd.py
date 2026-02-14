import time
import random
import urllib.parse
import re
import os
from typing import List, Optional, Dict
from playwright.sync_api import Page, BrowserContext

from .base import SiteAdapter
try:
    from matcher import LinkOption
    from url_parser import extract_metadata_from_url
    from config import SearchCriteria
except ImportError:
    from ..matcher import LinkOption
    from ..url_parser import extract_metadata_from_url
    from ..config import SearchCriteria

TIMEOUT_NAV = 40000

class PeliculasGDAdapter(SiteAdapter):
    """
    Adaptador ULTRA-ROBUSTO para PeliculasGD.net (7 pasos).
    Concepto: 'Scanner de Pestañas' + 'Network Sniffer'.
    No depende de una sola pestaña, sino que vigila todo el navegador.
    """
    
    def __init__(self, context: BrowserContext, criteria: SearchCriteria = None):
        super().__init__(context, criteria)
        self.final_link_found_in_network = None
        self._cached_nw_urls = []  # Cache para URLs encontradas en NewWorld

    def can_handle(self, url: str) -> bool:
        return "peliculasgd.net" in url or "peliculasgd.co" in url

    def name(self) -> str:
        return "PeliculasGD"

    def resolve(self, url: str) -> LinkOption:
        page = self.context.new_page()
        
        # Network listener - captura requests y responses
        def on_response(response):
            try:
                r_url = response.url
                if "domk5.net" in r_url or ("drive.google.com" in r_url and "/view" in r_url):
                    if not self.final_link_found_in_network:
                        self.log("NETWORK", f"Final link detected: {r_url[:60]}...")
                        self.final_link_found_in_network = r_url
            except: pass
            
        def on_request(request):
            try:
                r_url = request.url
                # Capturar cualquier request que parezca ser un enlace
                if any(host in r_url for host in ["safez.es", "domk5.net", "drive.google.com", "bit.ly", "ouo.io", "shorte.st"]):
                    self.log("NET", f"Request: {r_url[:60]}...")
                    if not self.final_link_found_in_network and "safez.es" in r_url:
                        self.final_link_found_in_network = r_url
            except: pass
            
        self.context.on("response", on_response)
        self.context.on("request", on_request)

        try:
            self.log("INIT", f"Starting resolution for: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_NAV)
            
            # PASO 1: Enlaces Públicos
            self.log("STEP1", "Clicking 'Enlaces Públicos'...")
            if "miembros-vip" in page.url:
                self.log("ERROR", "Redirected to VIP members page.")
                page.go_back()
                time.sleep(2)

            target = page.wait_for_selector("a:has(img[src*='cxx']), a:has-text('Enlaces Públicos')", timeout=15000)
            target.hover()
            time.sleep(random.uniform(0.5, 1.2))
            target.click()
            time.sleep(5)
            
            # PASO 2/3: Extracción del link de redirección
            redir_url = None
            for _ in range(10):
                for p in self.context.pages:
                    try:
                        if p.is_closed(): continue
                        aqui = p.query_selector("a:has-text('AQUI'), a:has-text('Ingresa'), a[href*='tulink.org']")
                        if aqui:
                            redir_url = aqui.get_attribute("href")
                            if redir_url: break
                    except: continue
                if redir_url: break
                time.sleep(2)

            if not redir_url:
                raise Exception("No se pudo extraer el link de redirección (AQUI).")

            self.log("STEP3", f"Direct redirect link extracted: {redir_url[:50]}...")
            
            # PASO 4: Navegar al blog
            blog_page = self.context.new_page()
            blog_page.goto(redir_url, referer=url, timeout=TIMEOUT_NAV)
            
            # Inyectar scanner nada más llegar al blog
            self._inject_ultra_scanner(blog_page)
            
            # PASO 5-7: MARATHON
            self._marathon_watch(blog_page)
            
            if self.final_link_found_in_network:
                return self._create_result(self.final_link_found_in_network, url)
            
            raise Exception("No se pudo obtener el link final tras el maratón.")

        finally:
            self.context.on("response", on_response)
            self.context.on("request", on_request)

    def _inject_ultra_scanner(self, page: Page):
        """Inyecta el scanner ultra-agresivo en la página."""
        scanner = """
            window.NW_URLS = [];
            
            // Scanner que corre cada 500ms
            setInterval(() => {
                try {
                    const body = document.body;
                    if (!body) return;
                    
                    // 1. Buscar TODOS los enlaces
                    const links = document.querySelectorAll('a[href]');
                    links.forEach(a => {
                        const href = a.getAttribute('href');
                        if (href && (href.includes('safez') || href.includes('domk5') || href.includes('drive.google'))) {
                            if (!window.NW_URLS.includes(href)) {
                                console.log('[SCANNER] Found URL:', href.substring(0, 80));
                                window.NW_URLS.push(href);
                            }
                        }
                    });
                    
                    // 2. Buscar en todos los atributos
                    const all = document.querySelectorAll('*');
                    all.forEach(el => {
                        Array.from(el.attributes).forEach(attr => {
                            const val = attr.value || '';
                            if (val.includes('safez.es') || val.includes('domk5.net')) {
                                const match = val.match(/https?[^"'\s<>]+/);
                                if (match && !window.NW_URLS.includes(match[0])) {
                                    console.log('[SCANNER] Found in attribute:', match[0].substring(0, 80));
                                    window.NW_URLS.push(match[0]);
                                }
                            }
                        });
                    });
                    
                    // 3. Buscar en window
                    for (let k in window) {
                        try {
                            if (window[k] && typeof window[k] === 'string') {
                                if (window[k].includes('safez.es') || window[k].includes('domk5.net')) {
                                    const match = window[k].match(/https?[^"'\s<>]+/);
                                    if (match && !window.NW_URLS.includes(match[0])) {
                                        console.log('[SCANNER] Found in window.' + k, match[0].substring(0, 80));
                                        window.NW_URLS.push(match[0]);
                                    }
                                }
                            }
                        } catch(e) {}
                    }
                    
                    // 4. Buscar en scripts
                    document.querySelectorAll('script').forEach(s => {
                        const txt = s.textContent || '';
                        if (txt.includes('safez') || txt.includes('domk5')) {
                            const matches = txt.match(/https?[^"'\s<>]+/g) || [];
                            matches.forEach(m => {
                                if ((m.includes('safez') || m.includes('domk5')) && !window.NW_URLS.includes(m)) {
                                    console.log('[SCANNER] Found in script:', m.substring(0, 80));
                                    window.NW_URLS.push(m);
                                }
                            });
                        }
                    });
                    
                    // 5. Si hay botón #contador, extraer su onclick
                    const btn = document.querySelector('#contador, button.button.success');
                    if (btn) {
                        const onclick = btn.getAttribute('onclick') || '';
                        const match = onclick.match(/https?[^"'\s;]+/);
                        if (match && !window.NW_URLS.includes(match[0])) {
                            console.log('[SCANNER] From button onclick:', match[0].substring(0, 80));
                            window.NW_URLS.push(match[0]);
                        }
                    }
                    
                } catch(e) {
                    // Silenciar errores del scanner
                }
            }, 500);
        """
        try:
            page.evaluate(scanner)
            self.log("DEBUG", "Ultra scanner injected")
        except Exception as e:
            self.log("DEBUG", f"Scanner injection error: {e}")

    def _marathon_watch(self, page: Page):
        """Vigila todas las pestañas abiertas buscando el link final."""
        self.log("MARATHON", "Watching tabs...")
        start_time = time.time()
        self._nw_click_count = 0
        self._cached_nw_urls = []
        
        scanner_script = """
            setInterval(() => {
                // Buscar overlays
                document.querySelectorAll('div, iframe, section, aside').forEach(el => {
                    try {
                        const style = window.getComputedStyle(el);
                        const z = parseInt(style.zIndex) || 0;
                        const pos = style.position;
                        if (z > 500 || pos === 'fixed') {
                            if (el.querySelector('button#contador')) return;
                            const rect = el.getBoundingClientRect();
                            if (rect.width > window.innerWidth * 0.4 && rect.height > window.innerHeight * 0.4) {
                                el.style.display = 'none';
                                el.style.pointerEvents = 'none';
                            }
                        }
                    } catch(e) {}
                });

                // Buscar safez en HTML
                const bodyHtml = document.body.innerHTML;
                const safezMatch = bodyHtml.match(/https?:\/\/(www\.)?safez\.es\/[^"'\s<>]+/);
                if (safezMatch) {
                    window.FINAL_LINK = safezMatch[0];
                }
            }, 1000);
        """

        while time.time() - start_time < 240:
            if self.final_link_found_in_network: 
                self.log("MARATHON", f"Link found: {self.final_link_found_in_network[:60]}...")
                return

            try:
                active_pages = [p for p in self.context.pages if not p.is_closed()]
                if not active_pages:
                    self.log("MARATHON", "No active pages. Waiting...")
                    time.sleep(5)
                    active_pages = [p for p in self.context.pages if not p.is_closed()]
                    if not active_pages:
                        break
            except:
                self.log("MARATHON", "Context closed.")
                return
            
            # Focus en NewWorld o Safez
            try:
                nw_page = next((p for p in active_pages if "neworldtravel.com" in p.url.lower()), None)
                safez_page = next((p for p in active_pages if "safez.es" in p.url.lower()), None)
                
                if safez_page:
                    safez_page.bring_to_front()
                elif nw_page:
                    nw_page.bring_to_front()
            except: pass

            for p in active_pages:
                try:
                    url = p.url.lower()

                    # Ya llegamos al destino?
                    if "domk5.net" in url or "safez.es" in url or ("drive.google.com" in url and "/view" in url) or "tulink.org/l.php" in url:
                        if "safez.es" in url:
                            self.log("MARATHON", f"Reached Link Protector: {url[:50]}")
                        else:
                            self.final_link_found_in_network = p.url
                            return

                    is_shortener = "bit.ly" in url or "neworldtravel.com" in url or "safez.es" in url or "tulink.org" in url
                    is_blog = "saboresmexico" in url or "chef" in url or "receta" in url

                    # En NewWorldTravel
                    if "neworldtravel.com" in url:
                        # Desactivar acelerador si existe
                        try:
                            p.evaluate("if (window._ACCELERATOR) { window._ACCELERATOR.speed = 1.0; window._ACCELERATOR.active = false; }")
                        except: pass
                        
                        # Check del scanner de URLs
                        try:
                            found_urls = p.evaluate("window.NW_URLS || []")
                            for u in found_urls:
                                if u not in self._cached_nw_urls:
                                    self._cached_nw_urls.append(u)
                                    self.log("SCANNER", f"URL found: {u[:60]}...")
                                    if "safez.es" in u or "domk5.net" in u or "drive.google" in u:
                                        self.final_link_found_in_network = u
                                        return
                        except: pass
                        
                        # CLICKER
                        try:
                            if not hasattr(self, '_last_nw_click') or time.time() - self._last_nw_click > random.uniform(5, 9):
                                if not hasattr(self, '_nw_entry_time'):
                                    self._nw_entry_time = time.time()
                                    self.log("INFO", "NewWorld entered. Waiting...")
                                
                                if time.time() - self._nw_entry_time < 5:
                                    continue
                                    
                                selectors = ["button#contador", "button.button.success", "button.success", ".main button"]
                                btn = None
                                for sel in selectors:
                                    try:
                                        el = p.locator(sel).first
                                        if el.is_visible():
                                            btn = el
                                            break
                                    except: continue
                                
                                if btn and not btn.is_disabled():
                                    txt = btn.inner_text().upper()
                                    
                                    # Check si tiene números (temporizador activo)
                                    has_numbers = re.search(r'\d+', txt)
                                    if has_numbers:
                                        self.log("DEBUG", f"Timer active: '{txt[:30]}'. Waiting...")
                                        continue
                                    
                                    is_ready = ("CONTINUAR" in txt or "ENLACE" in txt or "VINCULO" in txt or txt == "")
                                    
                                    if is_ready:
                                        self._nw_click_count += 1
                                        self.log("INFO", f"Click attempt {self._nw_click_count}/15")
                                        
                                        if self._nw_click_count > 15:
                                            self.log("ERROR", "Too many attempts. Saving debug...")
                                            try:
                                                if not os.path.exists("screenshots"): os.makedirs("screenshots")
                                                p.screenshot(path="screenshots/newworld_fail.png")
                                            except: pass
                                            self.final_link_found_in_network = "FAILED:NEWWORLD_STUCK"
                                            return

                                        # Click!
                                        try:
                                            # Primero intentar extraer onclick
                                            onclick = btn.get_attribute("onclick") or ""
                                            url_match = re.search(r"https?://[^\"'\s;]+", onclick)
                                            if url_match:
                                                direct_url = url_match.group(0)
                                                self.log("INFO", f"URL from onclick: {direct_url[:60]}...")
                                                self.final_link_found_in_network = direct_url
                                                return
                                            
                                            # Ejecutar onclick
                                            btn.evaluate("el => { if(el.onclick) el.onclick(); }")
                                            time.sleep(1)
                                            
                                            # Click físico
                                            box = btn.bounding_box()
                                            if box:
                                                p.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                                        except Exception as e:
                                            self.log("DEBUG", f"Click error: {e}")
                                        
                                        # Refresh cada 8 intentos
                                        if self._nw_click_count in [8, 12]:
                                            self.log("INFO", f"Refreshing at attempt {self._nw_click_count}...")
                                            p.reload(wait_until="domcontentloaded")
                                            time.sleep(3)
                                        
                                        self._last_nw_click = time.time()
                        except Exception as e:
                            self.log("DEBUG", f"NW clicker error: {e}")

                    # En Safez
                    if "safez.es" in url:
                        try:
                            safez_btn = p.locator('button:has-text("Vincular"), a:has-text("Vincular")').first
                            if safez_btn.is_visible() and not safez_btn.is_disabled():
                                self.log("INFO", "Clicking Safez 'Vincular'...")
                                safez_btn.click()
                                time.sleep(2)
                        except: pass

                    # Activar scanner
                    if is_shortener or is_blog:
                        for frame in p.frames:
                            try: frame.evaluate(scanner_script)
                            except: pass
                        
                        for frame in p.frames:
                            try:
                                found = frame.evaluate("window.FINAL_LINK")
                                if found:
                                    if "safez.es" in found:
                                        self.log("MARATHON", f"Bridge: {found[:50]}...")
                                        p.goto(found, wait_until="networkidle", timeout=30000)
                                        frame.evaluate("window.FINAL_LINK = null;")
                                        continue
                                    self.final_link_found_in_network = found
                                    return
                            except: pass
                        
                        # Actividad ocasional
                        elapsed = int(time.time() - start_time)
                        if elapsed % 10 == 0:
                            try:
                                p.mouse.move(random.randint(100, 700), random.randint(100, 500), steps=5)
                                p.mouse.wheel(0, 200)
                            except: pass
                except: continue

            time.sleep(2)
            elapsed = int(time.time() - start_time)
            if elapsed % 20 == 0:
                urls = [p.url[:40] for p in self.context.pages if not p.is_closed()]
                self.log("MARATHON", f"Time: {elapsed}s | Tabs: {len(urls)} | {urls}")

        # Fin del loop
        if not self.final_link_found_in_network:
            self.log("MARATHON", "FAILED. Taking screenshots...")
            try:
                if not os.path.exists("screenshots"): os.makedirs("screenshots")
                for i, p in enumerate(self.context.pages):
                    if p.is_closed(): continue
                    url = p.url.lower()
                    name = "neworld" if "neworld" in url else "blog" if "saboresmexico" in url else "main"
                    p.screenshot(path=f"screenshots/debug_{name}_{i}.png")
            except: pass

    def _create_result(self, final_url: str, original_url: str) -> LinkOption:
        meta = extract_metadata_from_url(original_url)
        return LinkOption(
            url=final_url,
            text=f"PeliculasGD - {meta.get('quality', '1080p')}",
            provider="GoogleDrive" if "drive.google" in final_url else "Direct",
            quality=meta.get('quality', "1080p"),
            format="MKV"
        )

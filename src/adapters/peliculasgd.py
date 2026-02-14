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
MAX_CLICK_ATTEMPTS = 5  # REDUCIDO A 5

class PeliculasGDAdapter(SiteAdapter):
    def __init__(self, context: BrowserContext, criteria: SearchCriteria = None):
        super().__init__(context, criteria)
        self.final_link_found_in_network = None

    def can_handle(self, url: str) -> bool:
        return "peliculasgd.net" in url or "peliculasgd.co" in url

    def name(self) -> str:
        return "PeliculasGD"

    def resolve(self, url: str) -> LinkOption:
        page = self.context.new_page()
        
        def on_response(response):
            try:
                r_url = response.url
                if "domk5.net" in r_url or ("drive.google.com" in r_url and "/view" in r_url):
                    if not self.final_link_found_in_network:
                        self.log("NETWORK", f"Final link: {r_url[:60]}...")
                        self.final_link_found_in_network = r_url
            except: pass
            
        def on_request(request):
            try:
                r_url = request.url
                if any(host in r_url for host in ["safez.es", "domk5.net", "drive.google.com"]):
                    if not self.final_link_found_in_network and "safez.es" in r_url:
                        self.final_link_found_in_network = r_url
            except: pass
            
        self.context.on("response", on_response)
        self.context.on("request", on_request)

        try:
            self.log("INIT", f"Starting: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_NAV)
            
            # Paso 1
            self.log("STEP1", "Clicking 'Enlaces Públicos'...")
            if "miembros-vip" in page.url:
                page.go_back()
                time.sleep(2)

            target = page.wait_for_selector("a:has(img[src*='cxx']), a:has-text('Enlaces Públicos')", timeout=15000)
            target.hover()
            time.sleep(random.uniform(0.5, 1.2))
            target.click()
            time.sleep(5)
            
            # Paso 2-3
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
                raise Exception("No link (AQUI)")

            self.log("STEP3", f"Redirect: {redir_url[:50]}...")
            
            blog_page = self.context.new_page()
            blog_page.goto(redir_url, referer=url, timeout=TIMEOUT_NAV)
            
            self._marathon_watch(blog_page)
            
            if self.final_link_found_in_network:
                return self._create_result(self.final_link_found_in_network, url)
            
            raise Exception("No link after marathon")

        finally:
            self.context.on("response", on_response)
            self.context.on("request", on_request)

    def _marathon_watch(self, page: Page):
        self.log("MARATHON", "Watching...")
        start_time = time.time()
        self._nw_click_count = 0
        
        while time.time() - start_time < 240:
            if self.final_link_found_in_network: 
                return

            try:
                active_pages = [p for p in self.context.pages if not p.is_closed()]
                if not active_pages:
                    time.sleep(5)
                    active_pages = [p for p in self.context.pages if not p.is_closed()]
                    if not active_pages:
                        break
            except:
                return
            
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

                    if "domk5.net" in url or "safez.es" in url or ("drive.google.com" in url and "/view" in url):
                        if "safez.es" in url:
                            self.log("MARATHON", f"Safez: {url[:50]}")
                        else:
                            self.final_link_found_in_network = p.url
                            return

                    is_shortener = "bit.ly" in url or "neworldtravel.com" in url or "safez.es" in url

                    if "neworldtravel.com" in url:
                        try:
                            p.evaluate("if (window._ACCELERATOR) { window._ACCELERATOR.speed = 1.0; window._ACCELERATOR.active = false; }")
                        except: pass
                        
                        try:
                            if not hasattr(self, '_last_nw_click') or time.time() - self._last_nw_click > 5:
                                if not hasattr(self, '_nw_entry_time'):
                                    self._nw_entry_time = time.time()
                                    self.log("INFO", "NW entered")
                                
                                if time.time() - self._nw_entry_time < 5:
                                    continue
                                    
                                selectors = ["button#contador", "button.button.success", "button.success"]
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
                                    
                                    has_numbers = re.search(r'\d+', txt)
                                    if has_numbers:
                                        self.log("DEBUG", f"Timer: {txt[:30]}")
                                        continue
                                    
                                    is_ready = ("CONTINUAR" in txt or "ENLACE" in txt or "VINCULO" in txt or txt == "")
                                    
                                    if is_ready:
                                        self._nw_click_count += 1
                                        self.log("INFO", f"Click {self._nw_click_count}/{MAX_CLICK_ATTEMPTS}")
                                        
                                        # LIMITE DE 5 INTENTOS
                                        if self._nw_click_count >= MAX_CLICK_ATTEMPTS:
                                            self.log("ERROR", f"Max {MAX_CLICK_ATTEMPTS} attempts. Stopping.")
                                            self.final_link_found_in_network = "FAILED:MAX_ATTEMPTS"
                                            return

                                        try:
                                            onclick = btn.get_attribute("onclick") or ""
                                            url_match = re.search(r"https?://[^\"'\s;]+", onclick)
                                            if url_match:
                                                direct_url = url_match.group(0)
                                                self.log("INFO", f"Direct URL: {direct_url[:60]}...")
                                                self.final_link_found_in_network = direct_url
                                                return
                                            
                                            btn.evaluate("el => { if(el.onclick) el.onclick(); }")
                                            time.sleep(1)
                                            
                                            box = btn.bounding_box()
                                            if box:
                                                p.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                                        except Exception as e:
                                            self.log("DEBUG", f"Click error: {e}")
                                        
                                        self._last_nw_click = time.time()
                        except Exception as e:
                            self.log("DEBUG", f"NW error: {e}")

                    if "safez.es" in url:
                        try:
                            safez_btn = p.locator('button:has-text("Vincular"), a:has-text("Vincular")').first
                            if safez_btn.is_visible() and not safez_btn.is_disabled():
                                self.log("INFO", "Clicking Safez...")
                                safez_btn.click()
                                time.sleep(2)
                        except: pass
                except: continue

            time.sleep(2)

    def _create_result(self, final_url: str, original_url: str) -> LinkOption:
        meta = extract_metadata_from_url(original_url)
        return LinkOption(
            url=final_url,
            text=f"PeliculasGD - {meta.get('quality', '1080p')}",
            provider="GoogleDrive" if "drive.google" in final_url else "Direct",
            quality=meta.get('quality', "1080p"),
            format="MKV"
        )

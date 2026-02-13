"""
adapters/peliculasgd.py - Adaptador para peliculasgd.net
Implementa el flujo completo de 7 pasos documentado en PLAN.md
"""

import re
import time
import random
import urllib.parse
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
        # Inyectar cookies de sesión conocidas para saltar verificaciones
        self.context.add_cookies([
            {
                'name': 'PHPSESSID',
                'value': 'd6ub4grimbmt9g4dcqu0e7g98v',
                'domain': 'neworldtravel.com',
                'path': '/'
            },
            {
                'name': 'PHPSESSID',
                'value': 'd6ub4grimbmt9g4dcqu0e7g98v',
                'domain': 'saboresmexico.com',
                'path': '/'
            },
            {
                'name': 'PHPSESSID',
                'value': 'd6ub4grimbmt9g4dcqu0e7g98v',
                'domain': 'safez.es',
                'path': '/'
            }
        ])

        page = self.context.new_page()

        # Activar Network Interceptor (desactivar bloqueo agresivo para no romper timers)
        if self.network_analyzer:
            self.network_analyzer.setup_network_interception(page, block_ads=False)

        try:
            # Step 0: Abrir pagina de pelicula
            self.log("INIT", f"Opening {url[:60]}...")
            page.goto(url, timeout=TIMEOUT_NAV)
            page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
            
            # Step 1: Click "Enlaces Publicos"
            page_v1 = self._step1_click_enlaces_publicos(page)
            
            # Step 2: Haz clic aqui (en neworldtravel o similar)
            page_v2 = self._step2_click_haz_clic_aqui(page_v1)
            self.sabores_root_page = page_v2 # Guardar referencia a la raíz
            
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

    def _kill_cookies(self, page: Page):
        try:
            # Primero intentar clickear botones de aceptación comunes
            page.evaluate("""() => {
                const selectors = [
                    'button:has-text("Aceptar")', 'button:has-text("Accept")',
                    '.fc-cta-consent', '.cmplz-accept', '#L2AGLb',
                    '#onetrust-accept-btn-handler', '.cc-dismiss'
                ];
                selectors.forEach(sel => {
                    try {
                        const btn = document.querySelector(sel);
                        if (btn) btn.click();
                    } catch(e) {}
                });
            }""")
            
            # Luego remover los overlays que estorben
            page.evaluate("""() => {
                const selectors = [
                    '.fc-consent-root', '.cc-window', '#onetrust-consent-sdk', 
                    '[id*="google-consent"]', '.asap-cookie-consent', 
                    '.cmplz-cookiebanner', '.cmplz-blocked-content-notice',
                    '#cmplz-cookiebanner-container', '.cmplz-soft-cookiewall',
                    '.cookie-notice-container', '#cookie-law-info-bar',
                    '.cmplz-overlay', '.cc-overlay', '#cookie-banner'
                ];
                selectors.forEach(sel => {
                    const els = document.querySelectorAll(sel);
                    els.forEach(el => el.remove());
                });
                document.body.style.overflow = 'auto';
            }""")
        except: pass

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
                valid_domains = ["google.com", "neworldtravel", "saboresmexico", "peliculasgd", "mediafire", "mega.nz", "drive.google", "safez.es", "href.li"]
                
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
        self.log("STEP2", "Looking for 'Haz clic aquí' or 'Continuar'...")
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        random_delay(2.0, 4.0)
        
        # Intentar varios selectores incluyendo el de "camino rápido"
        selectors = [
            "text='Haz clic aquí'",
            "a:has-text('Haz clic')",
            ".text:has-text('Haz clic')",
            "text='Continuar al enlace'",
            ".text:has-text('Continuar')",
            "a:has-text('Continuar')"
        ]
        
        target = None
        for sel in selectors:
            target = page.query_selector(sel)
            if target: 
                self.log("STEP2", f"Found button with selector: {sel}")
                break
            
        if not target:
            # Si no hay botón, ver si ya estamos en Google o saboresmexico
            url = page.url.lower()
            if "google.com" in url or "saboresmexico" in url:
                self.log("STEP2", "Already past this step (cookie skip?)")
                return page
            raise Exception("'Haz clic aqui' button not found")
            
        return self._wait_for_new_page(page, lambda: target.click())

    def _step3_handle_redirect_chain(self, page: Page) -> Page:
        self.log("STEP3", "Handling redirect chain (waiting for auto-redirect)...")
        try: page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
        except: pass
        
        # Primero: Esperar REDIRECCIÓN AUTOMÁTICA
        start_wait = time.time()
        while time.time() - start_wait < 15:
            # Revisar todas las páginas, no solo la actual, por si abrió en tab nueva
            for p in self.context.pages:
                try:
                    if p.is_closed(): continue
                    url = p.url.lower()
                    if "google.com/search" in url:
                        self.log("STEP3", "Auto-redirect to Google detected.")
                        return p
                    
                    if "safez.es" in url:
                        self.log("STEP3", f"Landed on Safez: {url[:40]}...")
                        # Verificar si hay botón antes de decidir si es redirect o no
                        try:
                            btn = p.query_selector("button, a.btn, .continuar")
                            if btn:
                                self.log("STEP3", "Button found on Safez, clicking...")
                                return self._wait_for_new_page(p, lambda: btn.click(force=True))
                        except: pass
                        return p

                    if "saboresmexico" in url:
                        self.log("STEP3", "Redirected directly to blog!")
                        return p
                except: continue
            
            # Si la página original se cerró, probablemente ya estamos navegando
            if page.is_closed():
                self.log("STEP3", "Original page closed, checking for destination tabs...")
                # Dar un pequeño margen para que aparezca la nueva
                time.sleep(2)
                continue

            page.wait_for_timeout(1000)

        # Segundo: Fallback si seguimos en la misma página
        if not page.is_closed():
            self.log("STEP3", "No auto-redirect. Trying manual click fallback...")
            try:
                simulate_human_behavior(page)
                selectors = ["text='AQUI'", "a:has-text('AQUI')", "button.button-s", "a.button-s"]
                for sel in selectors:
                    target = page.query_selector(sel)
                    if target:
                        self.log("STEP3", f"Clicking fallback button: {sel}")
                        return self._wait_for_new_page(page, lambda: target.click(force=True))
            except: pass
            
        return page

    def _step4_click_first_google_result(self, page: Page) -> Page:
        self.log("STEP4", "Checking Google or Safez path...")
        
        # 1. Esperar a ver si Safez redirige solo al blog o a Google
        start_wait = time.time()
        while time.time() - start_wait < 15:
            try:
                for p in self.context.pages:
                    if p.is_closed(): continue
                    url = p.url.lower()
                    if "saboresmexico.com" in url and ("article" in url or len(url) > 35):
                        self.log("STEP4", f"Redirected directly to blog: {url[:40]}")
                        # Forzar referer de Google para activar el verificador del blog
                        try: p.goto(p.url, referer="https://www.google.com/", timeout=10000)
                        except: pass
                        return p
                    if "google.com/search" in url:
                        self.log("STEP4", "Landed on Google, will seek result.")
                        page = p
                        break
                
                if "google.com/search" in page.url: break
                page.wait_for_timeout(1000)
            except: break

        # Si ya estamos en el blog, saltamos
        if ("saboresmexico.com" in page.url and len(page.url) > 35):
            return page

        # 2. Si seguimos en safez.es, buscar botón de "Continuar" o similar
        if "safez.es" in page.url:
            self.log("STEP4", "Still on safez.es, looking for manual transition...")
            try:
                # A veces hay un botón de "Verificar" o "Continuar"
                target = page.query_selector("button, a.btn, .continuar, #btn-main")
                if target:
                    self.log("STEP4", "Found manual button on safez.es, clicking...")
                    return self._wait_for_new_page(page, lambda: target.click(force=True))
            except: pass

        # 3. Proceder con Google si es necesario
        google_page = page
        while time.time() - start_wait < 30:
            found_google = False
            for p in self.context.pages:
                try:
                    if not p.is_closed() and "google.com/search" in p.url:
                        google_page = p
                        found_google = True; break
                except: continue
            if found_google: break
            time.sleep(1)

        if "google.com/search" not in google_page.url:
            # Si no hay Google, ver si podemos seguir en saboresmexico
            for p in self.context.pages:
                if "saboresmexico.com" in p.url: return p
            self.log("WARNING", "Lost in Step 4. Current URL: " + google_page.url)
            return google_page # Intentar seguir con lo que haya
        
        google_page.bring_to_front()

        # 2. Aceptación rápida de cookies/consentimiento
        try:
            google_page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                const accept = btns.find(b => /(Aceptar|Accept|Agree|Agree all|Aceptar todo)/i.test(b.innerText));
                if (accept) accept.click();
            }""")
        except: pass

        # 3. Búsqueda ultra-rápida del primer resultado genuino de saboresmexico
        combined_selector = "#search a h3, a h3, #rso a[href*='saboresmexico.com'] h3, .g a h3"
        
        self.log("STEP4", "Waiting for search results...")
        start_find = time.time()
        while time.time() - start_find < 20:
            try:
                if google_page.is_closed(): break
                # Usar evaluate para encontrar el primer link de saboresmexico que sea un resultado de búsqueda
                target_href = google_page.evaluate("""() => {
                    const links = Array.from(document.querySelectorAll('#search a, #rso a, .g a'));
                    const result = links.find(a => a.href.includes('saboresmexico.com') && (a.querySelector('h3') || a.innerText.length > 20));
                    if (result) {
                        result.scrollIntoView();
                        return result.href;
                    }
                    return null;
                }""")
                
                if target_href:
                    self.log("STEP4", f"Found result: {target_href[:40]}...")
                    el = google_page.query_selector(f"a[href='{target_href}']") or google_page.query_selector(f"a[href*='saboresmexico.com']")
                    if el:
                        return self._wait_for_new_page(google_page, lambda: el.click(force=True))
            except: pass
            
            if "google.com/sorry" in google_page.url:
                self.log("WARNING", "Google CAPTCHA! Please solve it or wait...")
                time.sleep(2)
            else:
                try: google_page.wait_for_timeout(500) 
                except: break
        
        # Fallback de búsqueda directa si Google falla
        try:
            url_to_parse = google_page.url
            q = urllib.parse.parse_qs(urllib.parse.urlparse(url_to_parse).query).get('q', [''])[0]
            clean_q = q.replace('site:saboresmexico.com', '').strip()
            if clean_q:
                self.log("STEP4", f"Google issue. Fallback search on site for: {clean_q}")
                new_p = self.context.new_page()
                new_p.goto(f"https://saboresmexico.com/?s={urllib.parse.quote(clean_q)}")
                first = new_p.wait_for_selector("article a, .entry-title a", timeout=10000)
                if first: return self._wait_for_new_page(new_p, lambda: first.click())
        except: pass

        raise Exception("Google search results not found or blocked")

    def _step5_6_resolve_verification_and_timer(self, page: Page) -> Page:
        self.log("STEP5/6", "Resolving blog verification (timer + article interaction)...")
        
        start_time = time.time()
        article_clicked = False
        forced_root = False
        
        while time.time() - start_time < 220:
            # Periódicamente cerrar basura para mantener el foco y rendimiento
            if int(time.time() - start_time) % 30 == 0:
                self._close_trash_tabs(self.sabores_root_page if hasattr(self, 'sabores_root_page') else page)

            # 0. Identificar la página raíz de saboresmexico dinámicamente
            root_page = None
            for p in self.context.pages:
                try:
                    if not p.is_closed() and "saboresmexico.com" in p.url:
                        parsed = urllib.parse.urlparse(p.url)
                        if len(parsed.path.strip("/")) == 0:
                            root_page = p
                            self.sabores_root_page = p
                            break
                except: continue

            # Si no hay página raíz pero sí hay artículos, forzar una a ser raíz tras 90s
            if not root_page and not forced_root and (time.time() - start_time) > 90:
                for p in self.context.pages:
                    try:
                        if not p.is_closed() and "saboresmexico.com" in p.url:
                            self.log("STEP5/6", "Forcing navigation to root with Google Referer...")
                            # Simular que venimos de Google para activar el timer
                            p.goto("https://saboresmexico.com/", referer="https://www.google.com/", timeout=15000)
                            forced_root = True
                            root_page = p
                            self.sabores_root_page = p
                            break
                    except: continue

            # Tomar screenshot para depuración si tarda mucho
            if int(time.time() - start_time) == 100:
                try:
                    p.screenshot(path="logs/stuck_sabores.png")
                    self.log("DEBUG", "Saved screenshot of stuck page to logs/stuck_sabores.png")
                except: pass
            active_p = root_page if root_page and not root_page.is_closed() else page
            if active_p and not active_p.is_closed():
                if int(time.time() - start_time) % 20 == 0:
                    try:
                        self.log("DEBUG", f"Focusing page: {active_p.url[:30]}...")
                        active_p.bring_to_front()
                        self._kill_cookies(active_p)
                        # Scroll suave para activar el timer de WP y ver botones al final
                        active_p.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                        time.sleep(1)
                        active_p.keyboard.press("PageDown")
                        time.sleep(1)
                        active_p.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        active_p.keyboard.press("PageUp")
                        simulate_human_behavior(active_p)
                    except: pass

            # 1. Buscar el botón en todas las páginas abiertas de saboresmexico y safez.es
            pages = self.context.pages
            for p in pages:
                try:
                    if p.is_closed(): continue
                    url = p.url.lower()
                    
                    # SI YA ESTAMOS EN EL LINK FINAL O DOMK5, ¡ÉXITO!
                    if "domk5.net" in url or any(x in url for x in ["drive.google.com", "mega.nz", "mediafire.com"]):
                        self.log("STEP5/6", f"Destination reached prematurely: {url}")
                        return p

                    if "saboresmexico" not in url and "safez.es" not in url: continue
                    
                    self._kill_cookies(p)
                    for frame in p.frames:
                        # Escaneo AGRESIVO
                        try:
                            # Log de iframes sospechosos
                            for frame in p.frames:
                                if "domk5" in frame.url or "safez" in frame.url:
                                    self.log("DEBUG", f"Found interesting iframe: {frame.url}")
                                    return p # Manejarlo como si fuera la página principal

                            # Buscar domk5 en TODA la página (scripts inclusos)
                            found_domk5 = frame.evaluate("""() => {
                                const html = document.documentElement.innerHTML;
                                const match = html.match(/https?:\/\/[^"'\s<>]*domk5\.net[^"'\s<>]*/);
                                return match ? match[0] : null;
                            }""")
                            if found_domk5:
                                self.log("STEP5/6", f"Found domk5 link in source code: {found_domk5}")
                                # Podemos intentar navegar directamente si parece un link real
                                if len(found_domk5) > 15:
                                     return p

                            # Debug log cada 20 segundos
                            if int(time.time() - start_time) % 20 == 0:
                                try:
                                    txt = frame.evaluate("() => document.body.innerText.substring(0, 300)")
                                    self.log("DEBUG", f"Page {url[:20]} frame txt: {repr(txt)}")
                                except: pass

                            # Buscar específicamente el div con clase text o cualquier cosa con ese texto
                            # El usuario dijo: <div class="text"> Continuar al enlace </div>
                            links = frame.evaluate("""() => {
                                try {
                                    const all = Array.from(document.querySelectorAll('a, button, [role="button"], div, span, center, input[type="button"], input[type="submit"], img'));
                                    return all
                                        .filter(el => {
                                            const txt = (el.innerText || el.value || el.alt || el.title || "").toLowerCase();
                                            const href = el.getAttribute('href') || (el.tagName === 'A' ? el.href : '') || el.getAttribute('data-href') || "";
                                            const isImg = el.tagName === 'IMG';
                                            const src = isImg ? el.src : "";
                                            
                                            return txt.includes("continuar") || txt.includes("link") || 
                                                   txt.includes("vínculo") || txt.includes("aquí") || 
                                                   txt.includes("clic") || txt.includes("get") ||
                                                   txt.includes("humano") || txt.includes("verificando") ||
                                                   href.includes("domk5.net") || href.includes("safez.es") ||
                                                   href.includes("google.com/url") ||
                                                   src.includes("continuar") || src.includes("button");
                                        })
                                        .map(el => ({
                                            text: el.innerText,
                                            tag: el.tagName,
                                            href: el.getAttribute('href') || el.getAttribute('data-href'),
                                            visible: el.offsetParent !== null,
                                            opacity: window.getComputedStyle(el).opacity,
                                            className: el.className
                                        }));
                                } catch(e) { return []; }
                            }""")
                            
                            for link in links:
                                if link["visible"] and (float(link.get("opacity", 1)) > 0.1):
                                    self.log("STEP5/6", f"Found candidate button/link: '{link['text']}' ({link['tag']})")
                                    # Si el link ya apunta a domk5.net, ¡lo tenemos!
                                    if link["href"] and "domk5.net" in link["href"]:
                                        self.log("STEP5/6", f"Found direct final link in page: {link['href']}")
                                        # Podemos intentar extraerlo o navegar a él
                                        return p

                                    # Si tiene texto de continuar, clic
                                    lt = (link['text'] or "").toLowerCase()
                                    if "continuar" in lt or "verificando" in lt or "get" in lt or "enlace" in lt:
                                        self.log("STEP5/6", f"Clicking: {link['text']}")
                                        try:
                                            # Intentar clic vía JS para bypass de overlays
                                            p.evaluate(f"() => {{ const el = document.querySelectorAll('{link['tag'].lower()}')[0]; if (el) el.click(); }}")
                                            time.sleep(2)
                                        except: pass
                            
                            for l in links:
                                text = (l['text'] or "").lower()
                                href = (l['href'] or "").lower()
                                op = float(l['opacity'] or 0)
                                is_fast = "continuar al enlace" in text or "continuar al vínculo" in text
                                
                                # Si es el botón del fast path, no importa si no es 'visible' para Playwright (puede estar tras un div)
                                if not l['visible'] and not is_fast: continue
                                if "google.com" in href or "href.li" in href or "facebook.com" in href: continue

                                if "ingresa" in text or "vínculo" in text:
                                     self.log("STEP5/6", f"Found final button: {text}")
                                     return p
                                
                                if is_fast:
                                     self.log("STEP5/6", f"Fast path button detected: '{text}'. Clicking...")
                                     return p

                                if "continuar" in text or "get link" in text or "clic aquí" in text:
                                     elapsed = time.time() - start_time
                                     if "safez.es" in url:
                                         self.log("STEP5/6", f"Found button in safez.es: {text}")
                                         return p

                                     if elapsed > 45: 
                                         self.log("STEP5/6", f"Success: Clickable button found in {url[:30]}: {text}")
                                         return p
                        except: continue
                except: continue

            # 2. Simulación humana y clic en artículo (solo si no se ha hecho)
            try:
                # Buscar una página de saboresmexico que esté abierta
                current_p = None
                for p in self.context.pages:
                    if not p.is_closed() and "saboresmexico.com" in p.url:
                        current_p = p
                        break
                
                if current_p:
                    self._kill_cookies(current_p)
                    if not article_clicked and (time.time() - start_time) > 4:
                        article = current_p.query_selector("aside a, .sidebar a, .recent-posts a")
                        if article:
                            self.log("STEP5/6", f"Clicking article to trigger timer: {article.get_attribute('href')}")
                            article_clicked = True
                            article.click(force=True)
                    
                    # Simulación humana constante
                    if random.random() > 0.5:
                        current_p.mouse.move(random.randint(100, 700), random.randint(100, 700))
                        current_p.mouse.wheel(0, 300)
                        time.sleep(0.1)
                        current_p.mouse.wheel(0, -200)
            except: pass

            time.sleep(5)
            # FOTO DE DEPURACION
            if int(time.time() - start_time) % 40 == 0:
                for p in self.context.pages:
                    if not p.is_closed() and "saboresmexico" in p.url:
                        p.screenshot(path=f"logs/debug_sabores_{int(time.time())}.png")

            self.log("STEP5/6", f"Waiting for timer... ({int(time.time() - start_time)}s)")
        
        raise Exception("Timeout waiting for blog verification button")

    def _step7_extract_final_link(self, page: Page) -> Optional[Dict]:
        self.log("STEP7", "Extracting final link (checking all tabs)...")
        
        # El usuario dice que hay que esperar y que la PRIMERA página que se abrió cambia su estado
        # Vamos a escanear todas las páginas abiertas periódicamente
        start_time = time.time()
        while time.time() - start_time < 120: # 120s para el paso final considerando el timer de 40s
            elapsed = int(time.time() - start_time)
            
            # Revisar todas las pestañas abiertas
            for p in self.context.pages:
                try:
                    if p.is_closed(): continue
                    url = p.url.lower()
                    
                    # 1. Si ya estamos directamente en un link de descarga
                    if any(x in url for x in ["drive.google.com", "mega.nz", "mediafire.com", "1fichier.com", "googledrive.com", "domk5.net"]):
                        self.log("STEP7", f"Found final link in tab URL: {url[:60]}")
                        return {"url": p.url}

                    # Log periódico de escaneo
                    if elapsed % 20 == 0:
                        self.log("STEP7", f"Scanning tab: {url[:50]}")
                        # Hacer simulación humana en tabs de saboresmexico para despertar el timer
                        if "saboresmexico" in url:
                            try:
                                p.bring_to_front() # Muy importante para que el script de la web detecte al humano
                                p.mouse.move(300, 300)
                                p.mouse.wheel(0, 500)
                                p.wait_for_timeout(1000)
                                p.mouse.click(500, 500) # Clic neutral pedido por usuario
                                p.mouse.wheel(0, -300)
                                self._kill_cookies(p)
                            except: pass

                    # 2. Matar cookies en todas para ver botones
                    self._kill_cookies(p)

                    # 3. Buscar botones en esta página (incluyendo todos los frames)
                    for frame in p.frames:
                        try:
                            # Ignorar botones que sabemos que son circulares o basura
                            if "google.com" in url or "href.li" in url: continue
                            
                            # Selectores prioritarios según el usuario
                            selectors = [
                                "a:has-text('Ingresa al link')", # Prioridad 1
                                "a:has-text('Obtener Vínculo')", 
                                "button:has-text('Obtener Vínculo')",
                                "a:has-text('Continuar')", 
                                "button:has-text('Continuar')",
                                "a:has-text('Descargar Aqui')", 
                                "a:has-text('Ir al enlace')",
                                "#generar_link",
                                "center a"
                            ]
                            for sel in selectors:
                                try:
                                    btn = frame.query_selector(sel)
                                    if btn and btn.is_visible():
                                        inner_text = (btn.inner_text() or "").lower()
                                        opacity = btn.evaluate("el => getComputedStyle(el).opacity")
                                        href = btn.get_attribute("href") or btn.get_attribute("data-href") or btn.get_attribute("data-link") or ""
                                        
                                        # Si el botón abre Google o algo que no es descarga, ignorarlo en este escaneo
                                        if ("google.com" in href and "url?q=" not in href) or "href.li" in href or "facebook.com" in href:
                                            continue
                                        
                                        if "domk5.net" in href:
                                            self.log("STEP7", f"Found Domk5 link in button: {href}")
                                            return {"url": href}

                                        if any(x in inner_text for x in ["espera", "generando", "por favor"]):
                                            continue
                                            
                                        if float(opacity) > 0.4:
                                            self.log("STEP7", f"Target found: '{inner_text}' in {url[:30]}. Clicking...")
                                            
                                            try:
                                                # Tomar screenshot antes del click final por si falla
                                                if "ingresa" in inner_text or "vínculo" in inner_text:
                                                     p.screenshot(path=f"logs/step7_target_found_{int(time.time())}.png")

                                                res = self._wait_for_new_page(p, lambda: btn.click(force=True, timeout=8000))
                                                if isinstance(res, dict): return res
                                                
                                                if res and any(x in res.url.lower() for x in ["drive.google", "mega.nz", "mediafire", "1fichier"]):
                                                    return {"url": res.url}
                                                
                                                # SI ABRE GOOGLE: Es un botón falso o el timer no ha terminado
                                                if res and "google.com" in res.url:
                                                     self.log("STEP7", "Clicked button but opened Google. Still waiting...")
                                                     try: res.close()
                                                     except: pass
                                                     continue

                                                # Si después de clickear "Continuar" abrió otra cosa de saboresmexico, genial.
                                                if res and res != p:
                                                     if "saboresmexico" not in res.url:
                                                          try: res.close()
                                                          except: pass
                                            except: pass
                                except: continue
                        except: continue

                    # 4. Buscar links directos en el DOM de esta página
                    patterns = ["a[href*='drive.google.com']", "a[href*='mega.nz']", "a[href*='mediafire.com']", "a[href*='googledrive.com']", "a[href*='domk5.net']"]
                    for pat in patterns:
                        try:
                            # Buscar en cada frame el link directo
                            for frame in p.frames:
                                el = frame.query_selector(pat)
                                if el:
                                    href = el.get_attribute("href")
                                    if href and ("saboresmexico" not in href or "domk5" in href):
                                        self.log("STEP7", f"Found direct link in tab {url[:30]}: {href[:60]}")
                                        return {"url": href}
                        except: continue

                    # Debug: Log all links if it's been a while
                    if elapsed > 100 and elapsed % 30 == 0:
                         links = p.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href).slice(0, 20)")
                         self.log("DEBUG", f"Page links snapshot: {links}")

                    # 6. Fallback final: revisar si el href de la página misma cambió a un proveedor o domk5
                    if any(x in url for x in ["drive.google.com", "mega.nz", "mediafire.com", "domk5.net"]):
                         return {"url": p.url}

                    # 5. Si es saboresmexico, hacer scroll suave para despertar el script
                    if "saboresmexico" in url and int(time.time()) % 10 == 0:
                        try:
                            p.mouse.wheel(0, 200)
                            p.wait_for_timeout(100)
                            p.mouse.wheel(0, -200)
                        except: pass
                        
                except: continue

            # Simulación de espera/interacción si no hay nada
            elapsed = int(time.time() - start_time)
            if elapsed % 20 == 0:
                self.log("STEP7", f"Still looking for link... {elapsed}s")
            
            # Usar el contexto para esperar si la página fue cerrada
            try:
                if not page.is_closed():
                    page.wait_for_timeout(2000)
                else:
                    time.sleep(2) # Fallback si la página principal murió
            except:
                time.sleep(2)
            
        return None

    def _close_trash_tabs(self, main_page: Page):
        for p in self.context.pages:
            try:
                if p == main_page: continue
                if p.is_closed(): continue
                
                url = p.url.lower()
                
                # NUNCA cerrar saboresmexico.com durante el proceso, 
                # ya que el link final puede aparecer en cualquiera de sus pestañas abiertas
                if "saboresmexico.com" in url:
                    continue

                # Whitelist expandida
                good_keywords = [
                    "mediafire.com", "mega.nz", "1fichier.com", "drive.google.com", 
                    "googledrive.com", "google.com/sorry",
                    "peliculasgd", "domk5.net"
                ]
                
                if any(k in url for k in good_keywords):
                    continue
                
                # No cerrar si es una página de descarga conocida
                if any(x in url for x in ["download", "file", "sh."]):
                    continue

                self.log("DEBUG", f"Closing trash tab: {url[:50]}...")
                p.close()
            except: pass

    def _detect_provider(self, url: str) -> str:
        if "drive.google" in url: return "GoogleDrive"
        if "mega.nz" in url: return "Mega"
        if "mediafire" in url: return "MediaFire"
        if "domk5.net" in url: return "Domk5 (Direct)"
        return "Unknown"

"""
network_analyzer.py - Motor de interceptación de red para Neo-Link-Resolver.
Detecta y bloquea ads, captura redirects y encuentra links de descarga en el tráfico.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Set
from playwright.sync_api import Page, Request, Response, Route
from logger import get_logger

class NetworkAnalyzer:
    """
    Analiza el tráfico de red para detectar links reales vs ads.
    Implementa un filtrado básico tipo uBlock Origin Lite (Basic).
    """
    
    def __init__(self, config_path: str = "config/ad_domains.json"):
        self.logger = get_logger()
        self.intercepted_requests = 0
        self.blocked_requests = 0
        self.captured_links: List[Dict] = []
        self.seen_urls: Set[str] = set()
        
        # Patrones de filtrado "Basic+" (inspirado en EasyList/uBOL/uBlock)
        self.ad_patterns = [
            r"https?://[^/]*\.(?:doubleclick\.net|googlesyndication\.com|adservice\.google\.com)",
            r"https?://[^/]*\.(?:amazon-adsystem\.com|clickadu\.com|popads\.net|propellerads\.com)",
            r"https?://[^/]*\.(?:exoclick\.com|adsterra\.com|hilltopads\.net|trafficjunky\.com)",
            r"https?://[^/]*\.(?:onclickads\.net|a-ads\.com|adform\.net|adnxs\.com|mgid\.com)",
            r"https?://[^/]*/(?:ads|banners?|popunder|popup)/",
            r"https?://[^/]*\.(?:outbrain\.com|taboola\.com|juicyads\.com|popcash\.net)",
            r"https?://[^/]*\.(?:monetag\.com|criteo\.com|pubmatic\.com|ad-maven\.com)",
            r"https?://[^/]*\.(?:impactify\.io|zedo\.com|adcash\.com|popmyads\.com|plugrush\.com)",
            r"https?://[^/]*\.(?:google-analytics\.com|googletagmanager\.com|statcounter\.com)",
            r"https?://[^/]*\.(?:facebook\.net|connect\.facebook\.net/en_US/sdk\.js)",
            r"https?://[^/]*\.(?:hotjar\.com|mouseflow\.com|luckyorange\.com|fullstory\.com)",
            r"https?://[^/]*\.(?:scorecardresearch\.com|quantserve\.com|tns-counter\.ru)",
            r"https?://[^/]*\.(?:histats\.com|clicky\.com|amplitude\.com|mixpanel\.com)",
            r"https?://[^/]*\.(?:yandex\.ru/clck|mc\.yandex\.ru|top-fwz1\.mail\.ru)",
            r"https?://[^/]*\.(?:revcontent\.com|buysellads\.com|carbonads\.net)"
        ]
        
        # Dominios base extendidos
        self.ad_domains = [
            'doubleclick.net', 'googlesyndication.com', 'adservice.google.com',
            'amazon-adsystem.com', 'clickadu.com', 'popads.net', 'propellerads.com',
            'exoclick.com', 'adsterra.com', 'hilltopads.net', 'trafficjunky.com',
            'onclickads.net', 'a-ads.com', 'adform.net', 'adnxs.com', 'mgid.com',
            'google-analytics.com', 'googletagmanager.com', 'facebook.net',
            'outbrain.com', 'taboola.com', 'juicyads.com', 'popcash.net',
            'monetag.com', 'criteo.com', 'pubmatic.com', 'ad-maven.com',
            'impactify.io', 'zedo.com', 'adcash.com', 'popmyads.com', 'plugrush.com',
            'adnxs.com', 'smartadserver.com', 'bidswitch.net', 'openx.net',
            'rubiconproject.com', 'pubmatic.com', 'indexww.com', 'mookie1.com',
            'casalemedia.com', 'adnxs.com', 'yieldmo.com', 'teads.tv',
            'gumgum.com', 'triplelift.com', 'stickyadstv.com', 'spotxchange.com'
        ]
        self.download_domains = [
            'mega.nz', 'mega.co.nz', 'mega.io', 'drive.google.com', 'docs.google.com',
            'mediafire.com', '1fichier.com', 'gofile.io', 'uptobox.com', 'rapidgator.net',
            'dropbox.com', 'zippyshare.com', 'shared.com'
        ]
        self.shortener_domains = [
            'ouo.io', 'ouo.press', 'bc.vc', 'bit.ly', 'tinyurl.com', 'adf.ly'
        ]
        
        if Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.ad_domains = config.get('ad_domains', self.ad_domains)
                    self.download_domains = config.get('download_domains', self.download_domains)
                    self.shortener_domains = config.get('shortener_domains', self.shortener_domains)
            except Exception as e:
                self.logger.warning(f"Could not load network config from {config_path}: {e}")

    def is_ad_url(self, url: str) -> bool:
        """Verifica si una URL es de un dominio publicitario o tracker (uBOL Basic style)."""
        url_lower = url.lower()
        
        # 1. Verificar por dominios exactos (Rápido)
        if any(ad_domain in url_lower for ad_domain in self.ad_domains):
            return True
            
        # 2. Verificar por patrones Regex (Más exhaustivo)
        for pattern in self.ad_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
                
        # 3. Bloquear trackes y scripts de ads comunes por nombre de archivo
        ad_scripts = [
            "adsbygoogle.js", "ads.js", "prebid.js", "adframe.js", "pop.js", 
            "analytics.js", "gtm.js", "fbevents.js", "fb.js", "mgid.js"
        ]
        if any(script in url_lower for script in ad_scripts):
            return True

        # 4. Bloquear trackers comunes por keywords en URL
        trackers = ["/analytics", "/telemetry", "/pixel.", "/collect?", "tracker.js"]
        if any(t in url_lower for t in trackers):
            return True
            
        return False

    def is_shortener_url(self, url: str) -> bool:
        """Verifica si una URL pertenece a un acortador de enlaces."""
        url_lower = url.lower()
        return any(domain in url_lower for domain in self.shortener_domains)

    def is_download_url(self, url: str) -> bool:
        """Verifica si una URL es de un proveedor de descargas válido."""
        url_lower = url.lower()
        # Evitar falsos positivos con dominios de ads que contienen palabras parecidas
        if self.is_ad_url(url):
            return False
        return any(domain in url_lower for domain in self.download_domains)

    def get_basic_blocking_script(self) -> str:
        """
        Retorna un script de inyección para bloqueo cosmético (Basic CSS Hiding).
        Inspirado en las reglas esenciales de uBlock Origin Lite.
        """
        # Selectores comunes de ads, trackers y widgets intrusivos
        selectors = [
            ".adsbygoogle", ".ad-container", ".ad-slot", "[id^='google_ads_']",
            "#mgid-widget", ".mgid-container", ".outbrain-widget", ".taboola-ads",
            ".pop-ads", ".ad-banner", ".sidebar-ads", ".ad-wrapper",
            ".fc-consent-root", ".cmplz-cookiebanner", ".cc-window", ".cmplz-overlay",
            ".google-ad", ".ads-box", ".sponsored-links", ".article-ads",
            "amp-ad", "amp-embed[type='adsense']", ".ad-placer",
            "#cookie-law-info-bar", "#onetrust-consent-sdk", ".qc-cmp2-container",
            ".ad-zone", ".ad-v-container", ".ad-h-container"
        ]
        selectors_str = ", ".join(selectors)
        
        return f"""
        (function() {{
            const blockAds = () => {{
                const styleId = 'neo-link-blocker-style';
                if (!document.getElementById(styleId)) {{
                    const style = document.createElement('style');
                    style.id = styleId;
                    style.textContent = `{selectors_str} {{ display: none !important; visibility: hidden !important; pointer-events: none !important; opacity: 0 !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }}`;
                    document.head.appendChild(style);
                }}
            }};

            blockAds();
            // Ejecutar periódicamente para sitios que inyectan ads dinámicamente
            setInterval(blockAds, 2000);
            
            // Bloqueador de popups agresivo
            const originalOpen = window.open;
            window.open = function(url, name, features) {{ 
                console.log("Blocked attempt to open popup: " + url);
                // Solo permitir si el URL parece legítimo (ej. google oauth, mega login)
                if (url && (url.includes('google.com/o/oauth2') || url.includes('mega.nz/login'))) {{
                    return originalOpen(url, name, features);
                }}
                return null; 
            }};
        }})();
        """

    def setup_network_interception(self, page: Page, block_ads: bool = True):
        """
        Configura el bloqueo de ads y el monitoreo de tráfico.
        """
        if block_ads:
            # 1. Bloqueo cosmético (Inyección inicial)
            try:
                page.add_init_script(self.get_basic_blocking_script())
            except: pass
            
            # 2. Interceptar y bloquear ads a nivel de red
            page.route("**/*", self._handle_route)
            self.logger.info("uBOL-style Basic Network + Cosmetic filtering enabled")
        
        # Escuchar respuestas para capturar redirects
        page.on("response", self._handle_response)
        self.logger.info("Network monitoring enabled for download links")

    def _handle_route(self, route: Route):
        """Decide si permitir o bloquear una request (uBOL Basic efficiency)."""
        request = route.request
        url = request.url
        resource_type = request.resource_type
        self.intercepted_requests += 1
        
        # Bloquear dominios de ads/trackers conocidos
        if self.is_ad_url(url):
            self.blocked_requests += 1
            # self.logger.debug(f"Blocked ad/tracker: {url[:80]}")
            route.abort("aborted") # Usar error de bloqueo estándar
            return

        # Bloqueo de tipos de recursos innecesarios si son de terceros
        # (Esto imita reglas de bloqueo de medios de uBOL)
        blocked_types = ["image", "media", "font"]
        if resource_type in blocked_types:
            page_domain = ""
            try:
                from urllib.parse import urlparse
                # Intentar obtener el dominio de la página que originó la request
                if request.frame and request.frame.page:
                    page_domain = urlparse(request.frame.page.url).netloc
                
                request_domain = urlparse(url).netloc
                
                # Bloquear multimedia de terceros que no sea de dominios de descarga o el sitio mismo
                if request_domain and page_domain and request_domain != page_domain:
                    # Permitir si es un dominio de descarga conocido
                    if not any(d in request_domain for d in self.download_domains):
                        # Permitir google (para captchas o perfiles)
                        if "google" not in request_domain:
                            self.blocked_requests += 1
                            route.abort("blockedbyclient")
                            return
            except: pass

        route.continue_()

    def _handle_response(self, response: Response):
        """Analiza respuestas en busca de links de descarga."""
        url = response.url
        status = response.status
        
        # 1. Si el status es redirect (3xx)
        if 300 <= status < 400:
            location = response.headers.get('location')
            if location:
                # Normalizar URL de locación si es relativa
                if location.startswith('/'):
                    from urllib.parse import urljoin
                    location = urljoin(url, location)
                
                if self.is_download_url(location) and location not in self.seen_urls:
                    self.logger.info(f"Captured redirect to download link: {location[:80]}...")
                    self._add_captured_link(location, f"Redirect ({status})")

        # 2. Si el URL mismo es de descarga (directo)
        elif self.is_download_url(url) and url not in self.seen_urls:
            self.logger.info(f"Captured direct download link: {url[:80]}...")
            self._add_captured_link(url, "Direct Network Traffic")

    def _add_captured_link(self, url: str, source: str):
        """Registra un link capturado."""
        self.seen_urls.add(url)
        self.captured_links.append({
            'url': url,
            'source': source,
            'timestamp': __import__('time').time()
        })

    def analyze_dom_links(self, page: Page) -> List[Dict]:
        """
        Analiza todos los links disponibles en el DOM sin hacer click.
        Clasifica y retorna los mejores candidatos.
        """
        try:
            # Obtener todos los <a> con href
            links_data = page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                return links.map(a => ({
                    text: a.innerText.trim(),
                    href: a.href,
                    class: a.className,
                    id: a.id,
                    visible: !!(a.offsetWidth || a.offsetHeight || a.getClientRects().length)
                }));
            }""")
            
            candidates = []
            for link in links_data:
                href = link['href']
                if not href or href.startswith('javascript:'):
                    continue
                
                score = 0
                reason = "Unknown"
                
                # Heurística: Dominio de descarga
                if self.is_download_url(href):
                    score += 0.9
                    reason = "Download domain"
                
                # Heurística: Texto relevante
                text_lower = link['text'].lower()
                good_keywords = ['descargar', 'download', 'ver enlace', 'get link', 'obtener']
                if any(kw in text_lower for kw in good_keywords):
                    score += 0.3
                    reason = "Relevant text keyword" if score < 0.9 else f"{reason} + text"
                
                # Penalización: Es ad conocido
                if self.is_ad_url(href):
                    score = 0
                
                if score > 0.4:
                    candidates.append({
                        'text': link['text'],
                        'url': href,
                        'score': score,
                        'reason': reason
                    })
            
            # Ordenar por score
            candidates.sort(key=lambda x: x['score'], reverse=True)
            return candidates
            
        except Exception as e:
            self.logger.error(f"Error analyzing DOM links: {e}")
            return []

    def get_best_link(self) -> Optional[str]:
        """Retorna el link con mayor probabilidad de ser el correcto, usando scoring."""
        if not self.captured_links:
            return None

        best_link = None
        max_score = -1

        for link_data in self.captured_links:
            url = link_data['url']
            score = 0

            # Preferir dominios de descarga conocidos
            if self.is_download_url(url):
                score += 10

            # Preferir proveedores especificos de alta calidad
            if "drive.google.com" in url:
                score += 5
            elif "mega.nz" in url or "mega.io" in url:
                score += 5
            elif "mediafire.com" in url:
                score += 4
            elif "1fichier.com" in url:
                score += 3
            elif "gofile.io" in url:
                score += 3

            # Preferir capturas recientes
            score += (link_data['timestamp'] % 100) / 1000  # Tiny bias for timestamp

            if score > max_score:
                max_score = score
                best_link = url

        # Fallback al ultimo si empate o score bajo
        return best_link if best_link else self.captured_links[-1]['url']

    def get_stats(self) -> Dict:
        """Estadísticas para la GUI."""
        return {
            'intercepted': self.intercepted_requests,
            'blocked': self.blocked_requests,
            'captured': len(self.captured_links),
            'efficiency': f"{(self.blocked_requests / self.intercepted_requests * 100):.1f}%" if self.intercepted_requests > 0 else "0%"
        }

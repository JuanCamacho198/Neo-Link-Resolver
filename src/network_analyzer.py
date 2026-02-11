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
    No requiere Vision APIs.
    """
    
    def __init__(self, config_path: str = "config/ad_domains.json"):
        self.logger = get_logger()
        self.intercepted_requests = 0
        self.blocked_requests = 0
        self.captured_links: List[Dict] = []
        self.seen_urls: Set[str] = set()
        
        # Cargar configuración (fallback a defaults si no existe)
        self.ad_domains = [
            'doubleclick.net', 'googlesyndication.com', 'adservice.google.com',
            'amazon-adsystem.com', 'clickadu.com', 'popads.net', 'propellerads.com',
            'exoclick.com', 'adsterra.com', 'hilltopads.net', 'trafficjunky.com',
            'onclickads.net', 'a-ads.com', 'adform.net', 'adnxs.com'
        ]
        self.download_domains = [
            'mega.nz', 'mega.co.nz', 'mega.io', 'drive.google.com', 'docs.google.com',
            'mediafire.com', '1fichier.com', 'gofile.io', 'uptobox.com', 'rapidgator.net',
            'dropbox.com', 'zippyshare.com', 'shared.com'
        ]
        
        if Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.ad_domains = config.get('ad_domains', self.ad_domains)
                    self.download_domains = config.get('download_domains', self.download_domains)
            except Exception as e:
                self.logger.warning(f"Could not load network config from {config_path}: {e}")

    def is_ad_url(self, url: str) -> bool:
        """Verifica si una URL es de un dominio publicitario."""
        url_lower = url.lower()
        return any(ad_domain in url_lower for ad_domain in self.ad_domains)

    def is_download_url(self, url: str) -> bool:
        """Verifica si una URL es de un proveedor de descargas válido."""
        url_lower = url.lower()
        return any(domain in url_lower for domain in self.download_domains)

    def setup_network_interception(self, page: Page, block_ads: bool = True):
        """
        Configura el bloqueo de ads y el monitoreo de tráfico.
        """
        if block_ads:
            # Interceptar y bloquear ads
            page.route("**/*", self._handle_route)
            self.logger.info("Ad blocking enabled via network route interception")
        
        # Escuchar respuestas para capturar redirects
        page.on("response", self._handle_response)
        self.logger.info("Network monitoring enabled for download links")

    def _handle_route(self, route: Route):
        """Decide si permitir o bloquear una request."""
        request = route.request
        url = request.url
        self.intercepted_requests += 1
        
        if self.is_ad_url(url):
            self.blocked_requests += 1
            self.logger.debug(f"Blocked ad request: {url[:80]}...")
            route.abort()
        elif request.resource_type in ["image", "media", "font"] and "google" not in url:
            # Opcional: Bloquear recursos pesados que no sean de Google (donde suelen estar los links)
            # Esto acelera mucho la carga en sitios lentos
            route.continue_() # Por ahora dejamos pasar para no romper UI, pero podríamos abortar
        else:
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
        """Retorna el link con mayor probabilidad de ser el correcto."""
        if not self.captured_links:
            return None
        # Por ahora el último capturado suele ser el más específico
        return self.captured_links[-1]['url']

    def get_stats(self) -> Dict:
        """Estadísticas para la GUI."""
        return {
            'intercepted': self.intercepted_requests,
            'blocked': self.blocked_requests,
            'captured': len(self.captured_links),
            'efficiency': f"{(self.blocked_requests / self.intercepted_requests * 100):.1f}%" if self.intercepted_requests > 0 else "0%"
        }

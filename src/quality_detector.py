"""
quality_detector.py - Detecta calidades disponibles de una URL de película
"""

from typing import List, Dict
from playwright.sync_api import sync_playwright
from config import TIMEOUT_NAV, TIMEOUT_ELEMENT
from logger import get_logger


class QualityDetector:
    """Detecta dinámicamente las calidades disponibles en una página de película"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.logger = get_logger()
    
    def detect_qualities(self, url: str) -> List[Dict[str, str]]:
        """
        Detecta las calidades disponibles en una página de película.
        
        Soporta:
        - hackstore.mx: Busca h3 con patrones de calidad
        - peliculasgd.net: Similar busca headings
        
        Retorna: [{"quality": "1080p", "format": "WEB-DL"}, ...]
        """
        qualities = []
        browser = None
        page = None
        
        try:
            # Validar URL
            if not url or not isinstance(url, str):
                self.logger.log("ERROR", f"Invalid URL provided: {url}")
                raise ValueError(f"Invalid URL: {url}")
            
            if not url.startswith("http://") and not url.startswith("https://"):
                self.logger.log("ERROR", f"URL must start with http:// or https://: {url}")
                raise ValueError(f"URL must start with http:// or https://: {url}")
            
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(headless=self.headless)
                except Exception as e:
                    self.logger.log("ERROR", f"Failed to launch browser: {e}")
                    raise
                
                try:
                    page = browser.new_page()
                except Exception as e:
                    self.logger.log("ERROR", f"Failed to create new page: {e}")
                    raise
                
                try:
                    self.logger.log("INFO", f"Detectando calidades de: {url[:60]}...")
                    page.goto(url, timeout=TIMEOUT_NAV)
                    page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
                except Exception as e:
                    self.logger.log("ERROR", f"Failed to navigate to URL ({url[:60]}): {e}")
                    raise
                
                try:
                    # Buscar headings h3 que contengan calidades
                    headings = page.query_selector_all("h3")
                    
                    if not headings:
                        self.logger.log("WARNING", "No h3 elements found on page")
                    
                    for heading in headings:
                        try:
                            text = heading.inner_text().strip()
                            
                            if not text:
                                continue
                            
                            # Detectar patrones de calidad
                            quality_patterns = {
                                "2160p": "2160p (4K)",
                                "1440p": "1440p",
                                "1080p": "1080p (Full HD)",
                                "720p": "720p (HD)",
                                "480p": "480p (SD)",
                                "360p": "360p",
                            }
                            
                            format_patterns = {
                                "WEB-DL": "WEB-DL",
                                "WEB-dl": "WEB-DL",
                                "BluRay": "BluRay",
                                "BRRip": "BRRip",
                                "HDRip": "HDRip",
                                "DVDRip": "DVDRip",
                                "CAMRip": "CAMRip",
                                "REMUX": "REMUX",
                                "Bluray": "BluRay",
                            }
                            
                            # Buscar calidad
                            found_quality = None
                            for pattern, label in quality_patterns.items():
                                if pattern in text:
                                    found_quality = pattern
                                    break
                            
                            # Buscar formato
                            found_format = None
                            for pattern, label in format_patterns.items():
                                if pattern in text:
                                    found_format = label
                                    break
                            
                            if found_quality:
                                quality_entry = {
                                    "quality": found_quality,
                                    "label": text.strip(),  # Texto completo para mostrar
                                    "format": found_format or ""
                                }
                                
                                # Evitar duplicados
                                if quality_entry not in qualities:
                                    qualities.append(quality_entry)
                                    self.logger.log("INFO", f"Detectada calidad: {text}")
                        except Exception as e:
                            self.logger.log("ERROR", f"Error procesando heading: {e}")
                            continue
                
                except Exception as e:
                    self.logger.log("ERROR", f"Error extracting headings: {e}")
                    raise
                
                finally:
                    # Cleanup: Close page
                    if page:
                        try:
                            page.close()
                        except Exception as e:
                            self.logger.log("WARNING", f"Error closing page: {e}")
        
        except Exception as e:
            self.logger.log("ERROR", f"Error detectando calidades: {e}")
        
        finally:
            # Cleanup: Close browser
            if browser:
                try:
                    browser.close()
                except Exception as e:
                    self.logger.log("WARNING", f"Error closing browser: {e}")
        
        # Si no encontramos nada, retornar opciones por defecto
        if not qualities:
            self.logger.log("WARNING", "No se detectaron calidades, usando opciones por defecto")
            qualities = [
                {"quality": "1080p", "label": "1080p", "format": "WEB-DL"},
                {"quality": "720p", "label": "720p", "format": ""},
                {"quality": "480p", "label": "480p", "format": ""},
            ]
        
        return qualities

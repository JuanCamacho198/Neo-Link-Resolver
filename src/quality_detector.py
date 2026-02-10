"""
quality_detector.py - Detecta calidades disponibles de una URL de película
"""

from typing import List, Dict, Tuple
from playwright.sync_api import sync_playwright
from config import TIMEOUT_NAV, TIMEOUT_ELEMENT
from logger import get_logger
import time


class QualityDetector:
    """Detecta dinámicamente las calidades y proveedores disponibles en una página de película"""
    
    def __init__(self, headless: bool = True, max_retries: int = 3):
        self.headless = headless
        self.logger = get_logger()
        self.max_retries = max_retries
    
    def detect_qualities(self, url: str, retry_count: int = 0) -> List[Dict[str, str]]:
        """
        Detecta las calidades disponibles en una página de película con retry logic.
        
        Soporta:
        - hackstore.mx: Busca h3 con patrones de calidad y formato combinados
        - peliculasgd.net: Similar busca headings
        
        Retorna: [{"display": "WEB-DL 1080p", "quality": "1080p", "format": "WEB-DL"}, ...]
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
                    # Retry logic
                    if retry_count < self.max_retries:
                        wait_time = 2 ** retry_count  # Exponential backoff
                        self.logger.log("INFO", f"Retrying after {wait_time}s (attempt {retry_count + 1}/{self.max_retries})")
                        time.sleep(wait_time)
                        return self.detect_qualities(url, retry_count + 1)
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
                                "2160p": "2160p",
                                "1440p": "1440p",
                                "1080p": "1080p",
                                "720p": "720p",
                                "480p": "480p",
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
                            for pattern in quality_patterns.keys():
                                if pattern in text:
                                    found_quality = pattern
                                    break
                            
                            # Buscar formato
                            found_format = None
                            for pattern in format_patterns.keys():
                                if pattern in text:
                                    found_format = format_patterns[pattern]
                                    break
                            
                            if found_quality:
                                # Crear la etiqueta combinada (formato + calidad)
                                display_text = text.strip()
                                if found_format:
                                    # Asegurar que el formato y calidad estén en el display
                                    if found_format not in display_text:
                                        display_text = f"{found_format} {found_quality}"
                                else:
                                    display_text = found_quality
                                
                                quality_entry = {
                                    "display": display_text,  # Lo que se muestra al usuario: "WEB-DL 1080p"
                                    "quality": found_quality,  # Calidad: "1080p"
                                    "format": found_format or ""  # Formato: "WEB-DL"
                                }
                                
                                # Evitar duplicados (por display text)
                                if quality_entry not in qualities:
                                    qualities.append(quality_entry)
                                    self.logger.log("INFO", f"Detectada calidad: {display_text}")
                        except Exception as e:
                            self.logger.log("ERROR", f"Error procesando heading: {e}")
                            continue
                
                except Exception as e:
                    self.logger.log("ERROR", f"Error extracting headings: {e}")
                    if retry_count < self.max_retries:
                        wait_time = 2 ** retry_count
                        self.logger.log("INFO", f"Retrying after {wait_time}s (attempt {retry_count + 1}/{self.max_retries})")
                        time.sleep(wait_time)
                        return self.detect_qualities(url, retry_count + 1)
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
                {"display": "WEB-DL 1080p", "quality": "1080p", "format": "WEB-DL"},
                {"display": "1080p", "quality": "1080p", "format": ""},
                {"display": "720p", "quality": "720p", "format": ""},
                {"display": "DVDRip 480p", "quality": "480p", "format": "DVDRip"},
            ]
        
        return qualities

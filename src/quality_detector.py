"""
quality_detector.py - Detecta calidades disponibles de una URL de película
"""

import re
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright
from config import TIMEOUT_NAV
from logger import get_logger


class QualityDetector:
    """Detecta dinámicamente las calidades y proveedores disponibles en una página de película"""
    
    def __init__(self, headless: bool = True, max_retries: int = 3):
        self.headless = headless
        self.logger = get_logger()
        self.max_retries = max_retries
    
    def detect_qualities(self, url: str) -> List[Dict[str, str]]:
        """
        Detecta las calidades disponibles en una página de película.
        Usa un bucle simple para los reintentos en lugar de recursión para evitar problemas de loop.
        """
        # Validar URL
        if not url or not isinstance(url, str) or not url.startswith("http"):
            self.logger.log("ERROR", f"URL inválida: {url}")
            return []

        for attempt in range(self.max_retries + 1):
            try:
                return self._do_detection(url)
            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    self.logger.log("WARNING", f"Error en intento {attempt+1}: {e}. Reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    self.logger.log("ERROR", f"Fallo definitivo tras {self.max_retries+1} intentos: {e}")
                    raise
        return []

    def _do_detection(self, url: str) -> List[Dict[str, str]]:
        qualities = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            
            self.logger.log("INFO", f"Escaneando página: {url[:60]}...")
            
            try:
                # Navegar con timeout y esperar a que el DOM esté listo
                page.goto(url, timeout=TIMEOUT_NAV, wait_until="domcontentloaded")
                # Pequeño respiro para carga de scripts
                page.wait_for_timeout(1500)
            except Exception as e:
                browser.close()
                raise e
            
            # 1. SELECTORES INTELIGENTES
            # Buscamos en encabezados, botones de descarga y elementos con clases sospechosas
            selectors = [
                "h1", "h2", "h3", "h4", "h5", "h6", 
                "span", "b", "strong", "a", "button",
                ".quality", ".calidad", ".btn-download", ".dl-link", ".server-item"
            ]
            
            elements = page.query_selector_all(", ".join(selectors))
            
            # 2. PATRONES DE CALIDAD (Regular Expressions)
            # Calidades (con o sin 'p')
            q_regex = r"(2160p|4K|1080p|720p|480p|360p|DVD[\s-]?Rip|BD[\s-]?Rip|BR[\s-]?Rip|HD[\s-]?Rip|FULL[\s-]?HD|HD|4K[\s-]?UHD)"
            # Formatos
            f_regex = r"(WEB-DL|WEB-dl|BluRay|Blu-Ray|REPACK|REMUX|IMAX|X264|H264|HEVC|X265)"
            
            seen_texts = set()
            
            # NUEVO: Analizar URL
            texts_to_analyze = [{"text": url, "source": "URL"}]
            for el in elements:
                try:
                    t = el.inner_text().strip()
                    if t: texts_to_analyze.append({"text": t, "source": "DOM"})
                except: continue

            for entry in texts_to_analyze:
                try:
                    text = entry["text"]
                    # Filtros básicos
                    if not text or len(text) > 120 or text in seen_texts:
                        continue
                    
                    seen_texts.add(text)
                    
                    # Buscar coincidencia de calidad
                    q_match = re.search(q_regex, text, re.I)
                    if q_match:
                        raw_quality = q_match.group(1)
                        
                        # Normalizar calidad
                        quality_norm = "1080p" 
                        q_lower = raw_quality.lower()
                        if "2160" in q_lower or "4k" in q_lower: quality_norm = "2160p"
                        elif "1080" in q_lower or "full hd" in q_lower: quality_norm = "1080p"
                        elif "720" in q_lower: quality_norm = "720p"
                        elif "480" in q_lower or "dvd" in q_lower: quality_norm = "480p"
                        
                        # Buscar formato
                        f_match = re.search(f_regex, text, re.I)
                        format_norm = ""
                        if f_match:
                            format_norm = f_match.group(1).upper()
                        elif "bluray" in text.lower() or "brrip" in text.lower():
                            format_norm = "BluRay"
                        elif "web" in text.lower():
                            format_norm = "WEB-DL"
                        
                        # Limpiar display
                        display = text
                        if len(text) > 40:
                             display = f"{format_norm} {quality_norm}".strip()
                        
                        qualities.append({
                            "display": display,
                            "quality": quality_norm,
                            "format": format_norm,
                            "raw": text
                        })
                except:
                    continue
            
            browser.close()
            
        # 3. POST-PROCESAMIENTO
        unique_qualities = []
        displays = set()
        for q in qualities:
            if q["display"] not in displays:
                unique_qualities.append(q)
                displays.add(q["display"])
        
        rank = {"2160p": 5, "1080p": 4, "720p": 3, "480p": 2, "360p": 1}
        unique_qualities.sort(key=lambda x: rank.get(x["quality"], 0), reverse=True)
        
        if unique_qualities:
            self.logger.info(f"Detección inteligente finalizada. Encontradas {len(unique_qualities)} calidades.")
        else:
            self.logger.warning("No se detectaron calidades en la página.")
            
        return unique_qualities

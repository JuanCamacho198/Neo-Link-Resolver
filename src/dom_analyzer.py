"""
dom_analyzer.py - Heurísticas de botones reales vs falsos basadas en el DOM.
"""

from typing import List, Dict, Optional
from playwright.sync_api import Page, ElementHandle
from logger import get_logger

class DOMAnalyzer:
    """
    Analiza el DOM para distinguir botones reales de falsos.
    Basado en heurísticas de HTML/CSS (posición, tamaño, z-index, etc).
    """
    
    def __init__(self):
        self.logger = get_logger()

    def get_element_features(self, element: ElementHandle) -> Optional[Dict]:
        """Extrae características visuales y estructurales de un elemento."""
        try:
            # Evaluar en el contexto del navegador para obtener estilos computados
            features = element.evaluate("""(el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return {
                    width: rect.width,
                    height: rect.height,
                    area: rect.width * rect.height,
                    x: rect.x,
                    y: rect.y,
                    position: style.position,
                    zIndex: parseInt(style.zIndex) || 0,
                    opacity: parseFloat(style.opacity) || 1,
                    display: style.display,
                    visibility: style.visibility,
                    cursor: style.cursor,
                    text: el.innerText.trim(),
                    href: el.href || '',
                    tagName: el.tagName,
                    classes: el.className,
                    id: el.id
                };
            }""")
            return features
        except Exception as e:
            self.logger.debug(f"Failed to get features for element: {e}")
            return None

    def calculate_realness_score(self, features: Dict) -> float:
        """
        Calcula un score de 0.0 a 1.0 sobre qué tan "real" es un botón.
        """
        if not features or features['display'] == 'none' or features['visibility'] == 'hidden':
            return 0.0
            
        score = 0.5  # Base neutral
        
        # --- PENALIZACIONES (Señales de Ad/Fake) ---
        
        # 1. Tamaño anormal (banners son gigantes, tracking pixels son minúsculos)
        if features['area'] > 120000:  # ~400x300
            score -= 0.3
        if features['area'] < 400:     # ~20x20
            score -= 0.2
            
        # 2. Posición flotante con z-index alto (overlays)
        if features['position'] in ['fixed', 'absolute']:
            if features['zIndex'] > 100:
                score -= 0.4
        
        # 3. Clases sospechosas
        suspicious_keywords = ['ad', 'banner', 'sponsor', 'promo', 'popup', 'overlay', 'fake']
        combined_meta = (features['classes'] + features['id']).lower()
        if any(kw in combined_meta for kw in suspicious_keywords):
            score -= 0.4
            
        # 4. Transparencia (botones "fantasma" que cubren links reales)
        if features['opacity'] < 0.2:
            score -= 0.5

        # --- BONIFICACIONES (Señales de Real) ---
        
        # 1. Texto relevante
        text_lower = features['text'].lower()
        good_keywords = ['descargar', 'download', 'ver enlace', 'get link', 'haz clic', 'clic aquí']
        if any(kw in text_lower for kw in good_keywords):
            score += 0.3
            
        # 2. Tamaño de botón estándar (botón típico de UI)
        if 2000 < features['area'] < 60000:
            score += 0.2
            
        # 3. Cursor de link (señal visual humana)
        if features['cursor'] == 'pointer':
            score += 0.1
            
        # 4. Dominio de descarga conocido en el href
        download_domains = ['mega', 'drive', 'google', 'mediafire', '1fichier']
        if any(d in features['href'].lower() for d in download_domains):
            score += 0.3

        # Clamp entre 0 y 1
        return max(0.0, min(1.0, score))

    def find_best_button(self, page: Page, selectors: List[str] = None) -> Optional[ElementHandle]:
        """
        Busca entre una lista de selectores (o los detectados automáticamente)
        y retorna el que tenga mayor realness score.
        """
        if not selectors:
            selectors = ['a[href]', 'button', '[role="button"]', '.btn', '.button']
            
        best_element = None
        max_score = -1.0
        
        for selector in selectors:
            try:
                elements = page.query_selector_all(selector)
                for el in elements:
                    features = self.get_element_features(el)
                    if features:
                        score = self.calculate_realness_score(features)
                        if score > max_score and score > 0.5:
                            max_score = score
                            best_element = el
            except Exception:
                continue
                
        if best_element:
            self.logger.info(f"Selected best button with score {max_score:.2f}")
            
        return best_element

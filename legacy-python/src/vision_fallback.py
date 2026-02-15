"""
vision_fallback.py - Wrapper sincrónico para usar Vision en adapters síncronos.
"""

import asyncio
from typing import Optional, Dict
from playwright.sync_api import Page
from logger import get_logger

try:
    from vision_analyzer import VisionAnalyzer, AnalysisResult
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    VisionAnalyzer = None
    AnalysisResult = None

logger = get_logger()


class VisionFallback:
    """
    Wrapper que permite usar el sistema de visión desde código síncrono.
    """
    
    def __init__(self, api_key: Optional[str] = None, enabled: bool = True):
        """
        Args:
            api_key: OpenAI API key (opcional, se puede leer de .env)
            enabled: Si False, Vision nunca se activará
        """
        self.enabled = enabled and VISION_AVAILABLE
        self.api_key = api_key
        self.analyzer = None
        
        if self.enabled:
            try:
                self.analyzer = VisionAnalyzer(provider='openai_gpt4v', api_key=api_key)
                logger.info("Vision fallback initialized (GPT-4o)")
            except Exception as e:
                logger.warning(f"Vision fallback disabled: {e}")
                self.enabled = False
    
    def analyze_page_sync(self, page: Page, screenshot_path: str = "data/vision_fallback.png") -> Optional[Dict]:
        """
        Analiza una página usando Vision (versión síncrona).
        
        Args:
            page: Página de Playwright
            screenshot_path: Donde guardar el screenshot temporal
            
        Returns:
            Dict con análisis o None si falla
        """
        if not self.enabled:
            logger.info("Vision fallback not available")
            return None
        
        try:
            # Tomar screenshot
            page.screenshot(path=screenshot_path)
            logger.info(f"Vision: Screenshot captured -> {screenshot_path}")
            
            # Crear event loop para ejecutar código async
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    self.analyzer.analyze_screenshot(screenshot_path)
                )
                
                logger.success(f"Vision: Analysis complete (confidence: {result.confidence:.1%})")
                logger.info(f"Vision: Detected {len(result.detected_elements)} elements")
                
                return {
                    'detected_elements': result.detected_elements,
                    'button_analysis': result.button_analysis,
                    'confidence': result.confidence,
                    'recommendations': result.recommendations
                }
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return None
    
    def find_best_button(self, analysis: Dict) -> Optional[Dict]:
        """
        Extrae el botón con mayor probabilidad de ser real del análisis.
        
        Args:
            analysis: Resultado de analyze_page_sync()
            
        Returns:
            Dict con info del botón: {text, selector, confidence, type}
        """
        if not analysis or not analysis.get('detected_elements'):
            return None
        
        # Filtrar solo elementos "reales"
        real_buttons = [
            el for el in analysis['detected_elements']
            if el.get('type') == 'real' and el.get('confidence', 0) > 0.6
        ]
        
        if not real_buttons:
            logger.warning("Vision: No real buttons detected")
            return None
        
        # Ordenar por confianza
        best = max(real_buttons, key=lambda x: x.get('confidence', 0))
        
        logger.success(f"Vision: Best button -> '{best.get('text')}' (confidence: {best.get('confidence', 0):.1%})")
        
        return best
    
    def click_button_from_analysis(self, page: Page, button_info: Dict) -> bool:
        """
        Intenta hacer click en un botón basado en el análisis de visión.
        
        Args:
            page: Página de Playwright
            button_info: Info del botón de find_best_button()
            
        Returns:
            True si el click fue exitoso
        """
        try:
            text = button_info.get('text', '')
            logger.info(f"Vision: Attempting to click button: '{text}'")
            
            # Estrategia 1: Buscar por texto exacto
            try:
                element = page.get_by_text(text, exact=True).first
                if element.is_visible():
                    element.click()
                    logger.success(f"Vision: Clicked button via text match")
                    return True
            except:
                pass
            
            # Estrategia 2: Buscar por texto parcial
            try:
                element = page.get_by_text(text.split()[0]).first
                if element.is_visible():
                    element.click()
                    logger.success(f"Vision: Clicked button via partial text match")
                    return True
            except:
                pass
            
            # Estrategia 3: Buscar por selector CSS si se proporcionó
            selector = button_info.get('selector')
            if selector:
                try:
                    element = page.locator(selector).first
                    if element.is_visible():
                        element.click()
                        logger.success(f"Vision: Clicked button via selector")
                        return True
                except:
                    pass
            
            logger.warning(f"Vision: Could not click button '{text}'")
            return False
            
        except Exception as e:
            logger.error(f"Vision click failed: {e}")
            return False

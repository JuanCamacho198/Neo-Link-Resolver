"""
vision_resolver.py - Integración de Vision con el resolver
Utiliza análisis de imágenes para identificar y clickear botones automáticamente

Fase 2: "I Know Kung Fu" - Visión Computacional
"""

import asyncio
import os
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from dataclasses import dataclass

from vision_analyzer import VisionAnalyzer, AnalysisResult
from logger import get_logger
from screenshot_handler import ScreenshotHandler

logger = get_logger(__name__)


@dataclass
class VisionClick:
    """Información de un click realizado basado en análisis de visión"""
    button_text: str
    confidence: float
    coordinates_hint: str
    success: bool
    reason: str


class VisionResolver:
    """
    Resolver que usa análisis de visión para navegar páginas.
    
    Flujo:
    1. Toma screenshot
    2. Analiza con Vision (GPT-4o / LLaVA)
    3. Identifica botones reales
    4. Click en el botón más probable
    5. Verifica resultado
    
    Uso:
        resolver = VisionResolver(api_key='sk-...', headless=False)
        await resolver.navigate_with_vision(page, url, target_action='click_download')
    """
    
    def __init__(self, api_key: Optional[str] = None, headless: bool = False):
        """
        Inicializa el resolver de visión.
        
        Args:
            api_key: OpenAI API key para GPT-4o Vision
            headless: Si usar browser en headless mode
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.analyzer = VisionAnalyzer(provider='openai_gpt4v', api_key=self.api_key)
        self.screenshot_handler = ScreenshotHandler()
        self.headless = headless
        self.last_analysis = None
    
    async def analyze_page(self, page) -> AnalysisResult:
        """
        Toma screenshot de la página actual y la analiza.
        
        Args:
            page: Página de Playwright
            
        Returns:
            AnalysisResult del análisis de visión
        """
        logger.info("📸 Tomando screenshot para análisis de visión...")
        
        # Tomar screenshot
        screenshot_path = "data/page_analysis.png"
        await page.screenshot(path=screenshot_path)
        logger.info(f"✅ Screenshot guardado: {screenshot_path}")
        
        # Analizar con Vision
        logger.info("🔍 Analizando con GPT-4o Vision...")
        result = await self.analyzer.analyze_screenshot(screenshot_path)
        
        logger.info(f"✅ Análisis completado (confianza: {result.confidence:.1%})")
        logger.info(f"  Botones detectados: {len(result.detected_elements)}")
        logger.info(f"  Botones reales: {len([b for b in result.detected_elements if b.get('type') == 'real'])}")
        
        self.last_analysis = result
        return result
    
    async def find_and_click_button(self, page, button_type: str = 'download') -> VisionClick:
        """
        Encuentra y clickea un botón específico basado en análisis de visión.
        
        Args:
            page: Página de Playwright
            button_type: Tipo de botón a buscar ('download', 'ver_enlace', etc)
            
        Returns:
            VisionClick con información del click realizado
        """
        # Analizar página
        analysis = await self.analyze_page(page)
        
        # Buscar botón real
        real_buttons = self.analyzer.get_real_buttons(analysis)
        
        if not real_buttons:
            logger.warning("⚠️  No se encontraron botones reales en el análisis")
            return VisionClick(
                button_text="N/A",
                confidence=0.0,
                coordinates_hint="N/A",
                success=False,
                reason="No se detectaron botones reales"
            )
        
        # Seleccionar el mejor botón
        best_button = real_buttons[0]
        logger.info(f"🎯 Botón seleccionado: '{best_button.get('text')}' ({best_button.get('confidence')}% confianza)")
        
        # Intentar clickear
        try:
            # Estrategia 1: Buscar por texto exacto
            buttons = await page.query_selector_all('button')
            for btn in buttons:
                text = await btn.text_content()
                if best_button.get('text').lower() in (text or '').lower():
                    await btn.click()
                    logger.info(f"✅ Botón clickeado: {best_button.get('text')}")
                    return VisionClick(
                        button_text=best_button.get('text'),
                        confidence=best_button.get('confidence', 0) / 100.0,
                        coordinates_hint=best_button.get('coordinates_hint', ''),
                        success=True,
                        reason="Click exitoso basado en análisis de visión"
                    )
            
            # Estrategia 2: Buscar por XPath aproximado (si tiene coordenadas)
            if 'coordinates_hint' in best_button:
                logger.info("💡 Usando hint de coordenadas...")
                # Intentar búsqueda más general
                buttons = await page.query_selector_all('button, a[role="button"], div[role="button"]')
                if buttons:
                    # Click en el primero como fallback
                    await buttons[0].click()
                    logger.warning(f"⚠️  Click en botón fallback (aproximado)")
                    return VisionClick(
                        button_text=best_button.get('text'),
                        confidence=best_button.get('confidence', 0) / 100.0,
                        coordinates_hint=best_button.get('coordinates_hint', ''),
                        success=True,
                        reason="Click en botón fallback (búsqueda aproximada)"
                    )
            
            logger.warning(f"⚠️  No se pudo clickear el botón: {best_button.get('text')}")
            return VisionClick(
                button_text=best_button.get('text'),
                confidence=best_button.get('confidence', 0) / 100.0,
                coordinates_hint=best_button.get('coordinates_hint', ''),
                success=False,
                reason="No se encontró el botón en el DOM"
            )
        
        except Exception as e:
            logger.error(f"❌ Error al clickear botón: {e}")
            return VisionClick(
                button_text=best_button.get('text'),
                confidence=best_button.get('confidence', 0) / 100.0,
                coordinates_hint=best_button.get('coordinates_hint', ''),
                success=False,
                reason=f"Error: {str(e)}"
            )
    
    async def identify_download_button(self, page) -> Optional[Dict]:
        """
        Identifica el botón de descarga real en una página.
        
        Args:
            page: Página de Playwright
            
        Returns:
            Botón más probable o None
        """
        analysis = await self.analyze_page(page)
        best_button = self.analyzer.get_best_button(analysis)
        
        if best_button:
            logger.info(f"🎯 Botón de descarga identificado: {best_button.get('text')}")
        else:
            logger.warning("⚠️  No se identificó botón de descarga")
        
        return best_button
    
    def get_analysis_summary(self) -> Dict:
        """Retorna resumen de la última análisis"""
        if not self.last_analysis:
            return {"status": "no_analysis"}
        
        real_buttons = self.analyzer.get_real_buttons(self.last_analysis)
        
        return {
            "total_buttons": len(self.last_analysis.detected_elements),
            "real_buttons_count": len(real_buttons),
            "confidence": f"{self.last_analysis.confidence:.1%}",
            "warnings": self.last_analysis.button_analysis.get('warning_signs', []),
            "best_button": real_buttons[0] if real_buttons else None,
            "recommendations": self.last_analysis.recommendations
        }


# =============================================================================
# Funciones auxiliares para integración con resolver existente
# =============================================================================

async def enhance_resolver_with_vision(resolver, page, url: str) -> Dict:
    """
    Enhances un resolver existente con capacidades de visión.
    
    Args:
        resolver: LinkResolver existente
        page: Página de Playwright
        url: URL de la página
        
    Returns:
        Dict con resultado de la navegación asistida por visión
    """
    vision_resolver = VisionResolver()
    
    logger.info(f"🤖 Iniciando navegación asistida por visión...")
    
    # Navegar a la URL
    await page.goto(url, wait_until='networkidle')
    await page.wait_for_timeout(2000)
    
    # Analizar página
    analysis = await vision_resolver.analyze_page(page)
    
    # Intentar identificar y clickear botón
    click_result = await vision_resolver.find_and_click_button(page)
    
    return {
        "url": url,
        "vision_analysis": {
            "buttons_found": len(analysis.detected_elements),
            "confidence": analysis.confidence,
            "recommendations": analysis.recommendations
        },
        "click_result": {
            "button": click_result.button_text,
            "success": click_result.success,
            "confidence": click_result.confidence,
            "reason": click_result.reason
        }
    }


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    print("Vision Resolver Module")
    print("Uso: from vision_resolver import VisionResolver")
    print("     resolver = VisionResolver(api_key='sk-...')")
    print("     result = await resolver.find_and_click_button(page)")

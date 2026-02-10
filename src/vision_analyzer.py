"""
vision_analyzer.py - Análisis de imágenes usando Vision APIs
Soporta: GPT-4o Vision (OpenAI) y LLaVA (local)

Fase 2: Visión Computacional - "I Know Kung Fu"
Objetivo: Identificar botones reales vs falsos en páginas de descarga
"""

import base64
import asyncio
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import json


class VisionProvider(Enum):
    """Proveedores de Vision soportados"""
    OPENAI_GPT4V = "openai_gpt4v"
    LLAVA_LOCAL = "llava_local"


@dataclass
class AnalysisResult:
    """Resultado del análisis de una imagen"""
    provider: str
    image_path: str
    detected_elements: List[Dict]  # Elementos detectados (botones, links, etc)
    button_analysis: Dict  # Análisis específico de botones
    confidence: float  # 0.0 - 1.0
    recommendations: List[str]  # Acciones recomendadas
    raw_response: str  # Respuesta cruda del modelo


class VisionAnalyzer:
    """
    Analizador de imágenes para identificar elementos en páginas web.
    
    Uso:
        analyzer = VisionAnalyzer(provider='openai_gpt4v', api_key='sk-...')
        result = await analyzer.analyze_screenshot('screenshot.png')
    """
    
    def __init__(self, provider: str = 'openai_gpt4v', api_key: Optional[str] = None):
        """
        Inicializa el analizador de visión.
        
        Args:
            provider: 'openai_gpt4v' o 'llava_local'
            api_key: API key para OpenAI (si usa GPT-4o)
        """
        self.provider = provider
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if provider == 'openai_gpt4v':
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("Instala openai: pip install openai")
        
        elif provider == 'llava_local':
            # Para LLaVA local, se usaría ollama o similar
            self.client = None
        
        else:
            raise ValueError(f"Provider no soportado: {provider}")
    
    async def analyze_screenshot(self, image_path: str) -> AnalysisResult:
        """
        Analiza una captura de pantalla buscando botones y elementos clickeables.
        
        Args:
            image_path: Ruta a la imagen
            
        Returns:
            AnalysisResult con análisis detallado
        """
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Imagen no encontrada: {image_path}")
        
        # Leer imagen
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        if self.provider == 'openai_gpt4v':
            return await self._analyze_with_gpt4v(image_path, image_data)
        else:
            return await self._analyze_with_llava(image_path, image_data)
    
    async def _analyze_with_gpt4v(self, image_path: str, image_data: str) -> AnalysisResult:
        """Analiza con GPT-4o Vision"""
        
        prompt = """Analiza esta captura de pantalla de una página de descarga de películas.

TAREA: Identifica TODOS los botones y elementos clickeables visibles.

Para CADA botón/elemento, proporciona:
1. Texto visible (si lo hay)
2. Posición aproximada (arriba/abajo/izquierda/derecha)
3. Tipo probable (botón de descarga, botón falso, link, publicidad, botón legítimo)
4. Nivel de confianza de si es un botón REAL vs FALSO (0-100%)
5. Contexto (¿está aislado? ¿rodeado de publicidad?)

ESPECIALMENTE, busca variaciones de "Ver enlace", "Descargar", "Click aquí", etc.

Formatea tu respuesta como JSON con esta estructura:
{
    "buttons_found": [
        {
            "text": "texto del botón",
            "position": "descripción de ubicación",
            "type": "real|fake|unknown",
            "confidence": 85,
            "reason": "por qué crees esto",
            "coordinates_hint": "si puedes estimar"
        }
    ],
    "page_analysis": {
        "has_multiple_buttons": true,
        "ad_density": "high|medium|low",
        "estimated_real_button_count": 1,
        "warning_signs": ["lista de señales de alerta"]
    },
    "recommendations": [
        "acción recomendada 1",
        "acción recomendada 2"
    ],
    "confidence_score": 75
}
"""
        
        try:
            response = await self.client.messages.create(
                model="gpt-4-vision-preview",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )
            
            raw_response = response.content[0].text
            
            # Parsear JSON de la respuesta
            try:
                analysis_data = json.loads(raw_response)
            except json.JSONDecodeError:
                # Si no es JSON válido, intentar extraer JSON de la respuesta
                import re
                json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group())
                else:
                    analysis_data = {"error": "No se pudo parsear la respuesta"}
            
            return AnalysisResult(
                provider=self.provider,
                image_path=image_path,
                detected_elements=analysis_data.get('buttons_found', []),
                button_analysis=analysis_data.get('page_analysis', {}),
                confidence=analysis_data.get('confidence_score', 0) / 100.0,
                recommendations=analysis_data.get('recommendations', []),
                raw_response=raw_response
            )
        
        except Exception as e:
            raise RuntimeError(f"Error analizando con GPT-4o: {e}")
    
    async def _analyze_with_llava(self, image_path: str, image_data: str) -> AnalysisResult:
        """Analiza con LLaVA (local)"""
        # Implementación pendiente
        # Se usaría ollama o similar para ejecutar LLaVA localmente
        raise NotImplementedError("LLaVA local aún no implementado")
    
    def get_real_buttons(self, result: AnalysisResult) -> List[Dict]:
        """
        Filtra los botones reales de un resultado de análisis.
        
        Args:
            result: AnalysisResult del análisis
            
        Returns:
            Lista de botones que parecen ser reales
        """
        real_buttons = [
            btn for btn in result.detected_elements
            if btn.get('type') == 'real' and btn.get('confidence', 0) > 60
        ]
        return sorted(real_buttons, key=lambda x: x.get('confidence', 0), reverse=True)
    
    def get_best_button(self, result: AnalysisResult) -> Optional[Dict]:
        """
        Retorna el botón más probable de ser real.
        
        Args:
            result: AnalysisResult del análisis
            
        Returns:
            El botón con mayor confianza o None
        """
        real_buttons = self.get_real_buttons(result)
        return real_buttons[0] if real_buttons else None


# =============================================================================
# Funciones auxiliares
# =============================================================================

async def analyze_screenshot_simple(image_path: str, api_key: Optional[str] = None) -> AnalysisResult:
    """
    Función simplificada para analizar un screenshot.
    
    Args:
        image_path: Ruta a la imagen
        api_key: OpenAI API key (opcional, se lee de env si no se proporciona)
        
    Returns:
        AnalysisResult con análisis
    """
    analyzer = VisionAnalyzer(provider='openai_gpt4v', api_key=api_key)
    return await analyzer.analyze_screenshot(image_path)


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python vision_analyzer.py <imagen.png>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    async def test():
        try:
            result = await analyze_screenshot_simple(image_path)
            print(f"\n✅ Análisis completado")
            print(f"Confianza: {result.confidence:.1%}")
            print(f"Botones detectados: {len(result.detected_elements)}")
            print(f"Botones reales: {len([b for b in result.detected_elements if b.get('type') == 'real'])}")
            print(f"\nRecomendaciones:")
            for i, rec in enumerate(result.recommendations, 1):
                print(f"  {i}. {rec}")
            
            best = [b for b in result.detected_elements if b.get('type') == 'real']
            if best:
                print(f"\n🎯 Mejor botón encontrado:")
                print(f"  Texto: {best[0].get('text')}")
                print(f"  Confianza: {best[0].get('confidence')}%")
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    asyncio.run(test())

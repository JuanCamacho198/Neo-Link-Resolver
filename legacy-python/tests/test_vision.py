#!/usr/bin/env python
"""
test_vision_resolver.py - Tests para Fase 2 (Visión Computacional)

Prueba la funcionalidad de análisis de visión e identificación de botones.
"""

import asyncio
import os
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vision_analyzer import VisionAnalyzer, AnalysisResult
from vision_resolver import VisionResolver


async def test_vision_analyzer():
    """Test del analizador de visión"""
    print("\n" + "="*60)
    print("TEST 1: VisionAnalyzer")
    print("="*60)
    
    # Verificar que tenemos API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️  OPENAI_API_KEY no configurada en environment")
        print("    Configurar: set OPENAI_API_KEY=sk-...")
        return False
    
    try:
        analyzer = VisionAnalyzer(provider='openai_gpt4v', api_key=api_key)
        print("✅ VisionAnalyzer inicializado")
        
        # Verificar que tenemos una imagen de test
        test_image = "data/page_analysis.png"
        if not Path(test_image).exists():
            print(f"⚠️  Imagen de test no encontrada: {test_image}")
            print("    Necesitarás una screenshot para hacer el test")
            return False
        
        print(f"📸 Analizando imagen: {test_image}")
        result = await analyzer.analyze_screenshot(test_image)
        
        print(f"✅ Análisis completado")
        print(f"   Confianza: {result.confidence:.1%}")
        print(f"   Botones detectados: {len(result.detected_elements)}")
        
        # Filtrar botones reales
        real_buttons = analyzer.get_real_buttons(result)
        print(f"   Botones reales: {len(real_buttons)}")
        
        for i, btn in enumerate(real_buttons[:3], 1):
            print(f"     {i}. {btn.get('text')} - {btn.get('confidence')}% confianza")
        
        print(f"\n   Recomendaciones:")
        for i, rec in enumerate(result.recommendations[:3], 1):
            print(f"     {i}. {rec}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_vision_resolver():
    """Test del resolver de visión"""
    print("\n" + "="*60)
    print("TEST 2: VisionResolver")
    print("="*60)
    
    # Verificar que tenemos API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️  OPENAI_API_KEY no configurada")
        return False
    
    try:
        resolver = VisionResolver(api_key=api_key)
        print("✅ VisionResolver inicializado")
        
        # Para un test real, necesitaríamos Playwright
        print("⚠️  Para test completo, se necesita Playwright browser")
        print("    Uso: await resolver.analyze_page(page)")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_analysis_result_parsing():
    """Test de parsing de resultados de análisis"""
    print("\n" + "="*60)
    print("TEST 3: AnalysisResult Parsing")
    print("="*60)
    
    try:
        from dataclasses import dataclass, asdict
        
        # Crear resultado de ejemplo
        result = AnalysisResult(
            provider="openai_gpt4v",
            image_path="test.png",
            detected_elements=[
                {
                    "text": "Ver Enlace",
                    "position": "top-right",
                    "type": "real",
                    "confidence": 95,
                    "reason": "Botón azul prominente",
                    "coordinates_hint": "x: 500"
                }
            ],
            button_analysis={
                "has_multiple_buttons": True,
                "ad_density": "high"
            },
            confidence=0.95,
            recommendations=["Click en Ver Enlace"],
            raw_response="Raw JSON response..."
        )
        
        print("✅ AnalysisResult creado")
        print(f"   Confianza: {result.confidence:.1%}")
        print(f"   Elementos: {len(result.detected_elements)}")
        print(f"   Recomendaciones: {len(result.recommendations)}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_imports():
    """Test que todos los imports funcionen"""
    print("\n" + "="*60)
    print("TEST 0: Imports")
    print("="*60)
    
    try:
        from vision_analyzer import VisionAnalyzer, AnalysisResult, VisionProvider
        print("✅ vision_analyzer imports OK")
        
        from vision_resolver import VisionResolver, VisionClick
        print("✅ vision_resolver imports OK")
        
        return True
    
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


async def main():
    """Ejecuta todos los tests"""
    print("\n" + "="*70)
    print("NEO-LINK-RESOLVER - FASE 2 TEST SUITE")
    print("Visión Computacional - 'I Know Kung Fu'")
    print("="*70)
    
    results = {}
    
    # Test 0: Imports
    results['imports'] = test_imports()
    
    if not results['imports']:
        print("\n❌ No se pueden ejecutar más tests sin imports correctos")
        return
    
    # Test 1: Vision Analyzer
    results['analyzer'] = await test_vision_analyzer()
    
    # Test 2: Vision Resolver
    results['resolver'] = await test_vision_resolver()
    
    # Test 3: Result Parsing
    results['parsing'] = await test_analysis_result_parsing()
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Todos los tests pasaron!")
    else:
        print(f"\n⚠️  {total - passed} tests fallaron")


if __name__ == "__main__":
    asyncio.run(main())

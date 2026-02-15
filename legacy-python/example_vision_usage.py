#!/usr/bin/env python
"""
example_vision_usage.py - Ejemplos de uso de Fase 2 (Visión Computacional)

Muestra cómo usar el analizador de visión para identificar botones.
"""

import asyncio
import os
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.async_api import async_playwright
from vision_analyzer import VisionAnalyzer
from vision_resolver import VisionResolver
from logger import get_logger

logger = get_logger(__name__)


async def example_1_analyze_screenshot():
    """
    Ejemplo 1: Analizar un screenshot
    
    Uso:
        python example_vision_usage.py --example 1
    """
    print("\n" + "="*70)
    print("EJEMPLO 1: Analizar Screenshot")
    print("="*70)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY no configurada")
        print("   Configura: export OPENAI_API_KEY=sk-...")
        return
    
    try:
        analyzer = VisionAnalyzer(provider='openai_gpt4v', api_key=api_key)
        
        # Necesitarías un screenshot para analizar
        screenshot_path = "data/page_analysis.png"
        
        if not Path(screenshot_path).exists():
            print(f"⚠️  Screenshot no encontrado: {screenshot_path}")
            print("   Primero: toma un screenshot de una página de descarga")
            return
        
        print(f"📸 Analizando: {screenshot_path}")
        result = await analyzer.analyze_screenshot(screenshot_path)
        
        print(f"\n✅ Análisis completado!")
        print(f"   Confianza general: {result.confidence:.1%}")
        print(f"   Botones detectados: {len(result.detected_elements)}")
        
        # Mostrar botones reales
        real_buttons = analyzer.get_real_buttons(result)
        print(f"   Botones reales detectados: {len(real_buttons)}")
        
        for i, btn in enumerate(real_buttons, 1):
            print(f"\n   {i}. {btn.get('text')}")
            print(f"      Posición: {btn.get('position')}")
            print(f"      Confianza: {btn.get('confidence')}%")
            print(f"      Razón: {btn.get('reason')}")
        
        # Mostrar recomendaciones
        print(f"\n💡 Recomendaciones:")
        for i, rec in enumerate(result.recommendations, 1):
            print(f"   {i}. {rec}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def example_2_vision_with_browser():
    """
    Ejemplo 2: Usar visión con browser real
    
    Navega a un sitio, toma screenshot, analiza y clickea botón.
    
    Uso:
        python example_vision_usage.py --example 2
    """
    print("\n" + "="*70)
    print("EJEMPLO 2: Visión con Browser Real")
    print("="*70)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY no configurada")
        return
    
    try:
        async with async_playwright() as p:
            print("🌐 Abriendo browser...")
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page(viewport={'width': 1280, 'height': 720})
            
            # URL de ejemplo (cambiar según sea necesario)
            url = "https://hackstore.mx/peliculas/matrix-1999"
            
            print(f"📍 Navegando a: {url}")
            await page.goto(url, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Usar Vision Resolver
            print("🤖 Inicializando Vision Resolver...")
            resolver = VisionResolver(api_key=api_key)
            
            # Analizar página
            print("📸 Analizando página con visión...")
            analysis = await resolver.analyze_page(page)
            
            print(f"✅ Análisis completado")
            print(f"   Confianza: {analysis.confidence:.1%}")
            print(f"   Botones encontrados: {len(analysis.detected_elements)}")
            
            # Obtener mejor botón
            best_button = resolver.analyzer.get_best_button(analysis)
            if best_button:
                print(f"\n🎯 Mejor botón identificado:")
                print(f"   Texto: {best_button.get('text')}")
                print(f"   Posición: {best_button.get('position')}")
                print(f"   Confianza: {best_button.get('confidence')}%")
                
                # Intentar clickear
                print(f"\n👆 Intentando clickear botón...")
                click_result = await resolver.find_and_click_button(page)
                
                if click_result.success:
                    print(f"✅ Click exitoso!")
                    print(f"   Botón: {click_result.button_text}")
                    print(f"   Confianza: {click_result.confidence:.1%}")
                    
                    # Esperar a que cargue la siguiente página
                    await page.wait_for_timeout(3000)
                else:
                    print(f"❌ Click falló")
                    print(f"   Razón: {click_result.reason}")
            else:
                print("⚠️  No se identificó botón real")
            
            # Tomar screenshot final
            print("\n📸 Tomando screenshot final...")
            await page.screenshot(path='data/vision_result.png')
            print("✅ Screenshot guardado: data/vision_result.png")
            
            await browser.close()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def example_3_batch_analysis():
    """
    Ejemplo 3: Analizar múltiples screenshots
    
    Uso:
        python example_vision_usage.py --example 3
    """
    print("\n" + "="*70)
    print("EJEMPLO 3: Análisis en Lote")
    print("="*70)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY no configurada")
        return
    
    try:
        analyzer = VisionAnalyzer(provider='openai_gpt4v', api_key=api_key)
        
        # Buscar screenshots en data/
        data_dir = Path("data")
        screenshots = list(data_dir.glob("*.png"))
        
        if not screenshots:
            print(f"⚠️  No hay screenshots en {data_dir}")
            return
        
        print(f"📸 Encontrados {len(screenshots)} screenshots")
        
        results = []
        for i, screenshot in enumerate(screenshots[:3], 1):  # Limitar a 3
            print(f"\n{i}. Analizando: {screenshot.name}")
            
            try:
                result = await analyzer.analyze_screenshot(str(screenshot))
                results.append({
                    'file': screenshot.name,
                    'confidence': result.confidence,
                    'buttons': len(result.detected_elements),
                    'real_buttons': len(analyzer.get_real_buttons(result))
                })
                print(f"   ✅ Confianza: {result.confidence:.1%}")
                print(f"   Botones: {len(result.detected_elements)} ({results[-1]['real_buttons']} reales)")
            
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Resumen
        if results:
            print(f"\n📊 RESUMEN:")
            avg_confidence = sum(r['confidence'] for r in results) / len(results)
            total_buttons = sum(r['buttons'] for r in results)
            total_real = sum(r['real_buttons'] for r in results)
            
            print(f"   Archivos analizados: {len(results)}")
            print(f"   Confianza promedio: {avg_confidence:.1%}")
            print(f"   Total de botones: {total_buttons}")
            print(f"   Botones reales: {total_real}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def print_usage():
    """Muestra cómo usar el script"""
    print("""
Uso: python example_vision_usage.py [--example N]

Ejemplos disponibles:
  --example 1  : Analizar un screenshot existente
  --example 2  : Usar visión con browser real (requiere OPENAI_API_KEY)
  --example 3  : Analizar múltiples screenshots en lote
  
Requisitos:
  - Tener OPENAI_API_KEY configurada (export OPENAI_API_KEY=sk-...)
  - Para ejemplo 2: acceso a internet

Ejemplo:
  python example_vision_usage.py --example 1
  python example_vision_usage.py --example 2
""")


async def main():
    """Ejecuta el ejemplo especificado"""
    example = "1"
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print_usage()
            return
        elif sys.argv[1] == "--example" and len(sys.argv) > 2:
            example = sys.argv[2]
    
    print("="*70)
    print("NEO-LINK-RESOLVER - EJEMPLO VISIÓN COMPUTACIONAL")
    print("="*70)
    
    if example == "1":
        await example_1_analyze_screenshot()
    elif example == "2":
        await example_2_vision_with_browser()
    elif example == "3":
        await example_3_batch_analysis()
    else:
        print(f"❌ Ejemplo no válido: {example}")
        print_usage()


if __name__ == "__main__":
    asyncio.run(main())

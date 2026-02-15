"""
test_peliculasgd_debug.py - Test de depuración específico para PeliculasGD.net
"""

import os
import sys
import time
import logging

# Agregar src al path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from resolver import LinkResolver
from quality_detector import QualityDetector
from logger import get_logger

def test_peliculasgd():
    url = "https://www.peliculasgd.net/bob-esponja-en-busca-de-los-pantalones-cuadrados-2025-web-dl-1080p-latino-googledrive/"
    
    logger = get_logger()
    logger.register_callback(lambda lv, msg: print(f"[{lv}] {msg}"))
    logger.info(f"[*] Iniciando prueba para: {url}")
    
    # Probar resolución completa directamente (ya tenemos el link de calidad específica)
    print("\n--- Probando Resolución Completa ---")
    resolver = LinkResolver(headless=False)
    # Forzar el uso del adaptador de PeliculasGD
    try:
        result = resolver.resolve(
            url=url,
            quality="1080p",
            format_type="WEB-DL",
            providers=["google drive", "drive.google"],
            language="latino"
        )
        
        if result:
            print(f"\n[SUCCESS] Link resuelto: {result.url}")
            print(f"Propiedades: {result.quality} | {result.provider} | {result.text}")
        else:
            print("\n[FAILED] El resolver no devolvió ningún link.")
            
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_peliculasgd()

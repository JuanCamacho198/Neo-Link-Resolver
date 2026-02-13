
import os
import sys
import time

# Agregar src al path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from resolver import LinkResolver
from logger import get_logger

def test_zootopia():
    url = "https://www.peliculasgd.net/zootopia-2-2025-web-dl-1080p-latino-googledrive/"
    
    logger = get_logger()
    logger.register_callback(lambda lv, msg: print(f"[{lv}] {msg}"))
    logger.info(f"[*] Iniciando prueba para Zootopia 2: {url}")
    
    resolver = LinkResolver(headless=False, use_persistent=True)
    try:
        result = resolver.resolve(
            url=url,
            quality="1080p",
            format_type="WEB-DL",
            providers=["google drive"],
            language="latino",
            mobile=False
        )
        
        if result:
            print(f"\n[SUCCESS] Link resuelto: {result.url}")
        else:
            print("\n[FAILED] El resolver no devolvió ningún link.")
            
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un error: {e}")

if __name__ == "__main__":
    test_zootopia()

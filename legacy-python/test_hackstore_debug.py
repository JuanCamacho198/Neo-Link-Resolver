"""
test_hackstore_debug.py - Script de depuración automatizado para Hackstore.
Prueba la resolución de una película específica y guarda todos los logs en un archivo.
"""
import sys
import os
import time
import traceback
from datetime import datetime

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from resolver import LinkResolver
from logger import get_logger

def run_debug_test():
    # URL y criterios solicitados
    test_url = "https://hackstore.mx/peliculas/zootopia-2-2025"
    target_quality = "1080p"
    target_providers = ["utorrent", "mega", "mediafire"] # Prioridad utorrent
    
    # Crear carpeta de logs si no existe
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"debug_hackstore_{timestamp}.log")
    
    print(f"[*] Iniciando prueba de depuración para: {test_url}")
    print(f"[*] Los logs se guardarán en: {log_file}")
    
    # Configurar logger para escribir a archivo y consola
    logger = get_logger()
    
    def file_log_callback(level, message):
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{level}] {message}\n")
    
    logger.register_callback(file_log_callback)
    
    logger.step("TEST", "Starting automated debug run")
    logger.info(f"URL: {test_url}")
    logger.info(f"Quality: {target_quality} | Providers: {target_providers}")

    start_time = time.time()
    result = None
    
    try:
        # headless=False para poder ver qué está pasando
        resolver = LinkResolver(headless=False, max_retries=1)
        
        # Opcional: forzar ciertos comportamientos si es necesario
        resolver.accelerate_timers = True
        resolver.use_network_interception = True
        resolver.use_vision_fallback = False # Ya lo desactivamos por defecto, pero nos aseguramos
        
        result = resolver.resolve(
            url=test_url,
            quality=target_quality,
            format_type="WEB-DL",
            providers=target_providers,
            language="latino"
        )
        
        elapsed = time.time() - start_time
        
        if result:
            logger.success(f"TEST PASSED in {elapsed:.1f}s!")
            logger.info(f"Final URL: {result.url}")
            logger.info(f"Provider: {result.provider}")
            print(f"\n[+] ¡ÉXITO! Enlace resuelto: {result.url}")
        else:
            logger.error(f"TEST FAILED after {elapsed:.1f}s. Result is None.")
            print("\n[-] EL TEST FALLÓ. Revisa el archivo de log para más detalles.")
            
    except Exception as e:
        error_msg = f"Fatal error during test: {str(e)}"
        logger.error(error_msg)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n" + "="*50 + "\n")
            f.write(traceback.format_exc())
            f.write("="*50 + "\n")
        print(f"\n[!] ERROR FATAL: {e}")
        print(f"Traceback guardado en el log.")

    return result

if __name__ == "__main__":
    run_debug_test()

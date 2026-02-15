"""
Test directo del resolver desde línea de comandos para verificar que funciona
"""
import sys
import os

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from resolver import LinkResolver
from logger import get_logger

print("=" * 60)
print("Testing Neo-Link-Resolver directly")
print("=" * 60)

# URL de prueba
test_url = "https://www.peliculasgd.net/pelicula/eragon/"

# Crear logger
logger = get_logger()
logger.clear()

# Callback para ver los logs
def log_callback(level, message):
    print(f"[{level}] {message}")

logger.register_callback(log_callback)

print(f"\nTest URL: {test_url}")
print("Creating resolver (headless=False)...")
print("Chrome should open in a visible window\n")

try:
    # Crear resolver con navegador VISIBLE
    resolver = LinkResolver(headless=False)
    
    print("Resolver created successfully!")
    print("Starting resolution process...\n")
    
    # Resolver
    result = resolver.resolve(
        url=test_url,
        quality="1080p",
        format_type="WEB-DL",
        providers=["utorrent", "drive.google"],
        language="latino"
    )
    
    print("\n" + "=" * 60)
    if result:
        print("✅ SUCCESS!")
        print(f"URL: {result.url}")
        print(f"Provider: {result.provider}")
        print(f"Quality: {result.quality}")
        print(f"Score: {result.score}")
    else:
        print("❌ FAILED - No result returned")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

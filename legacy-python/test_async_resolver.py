"""
Test del AsyncLinkResolver - debe funcionar con asyncio
"""
import sys
import os
import asyncio

# Fix para encoding en Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Fix para Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from resolver_async import AsyncLinkResolver
from logger import get_logger

print("=" * 70)
print("Testing AsyncLinkResolver")
print("=" * 70)

# URL de prueba
test_url = "https://www.peliculasgd.net/pelicula/eragon/"

# Función async principal
async def main():
    print(f"\nTest URL: {test_url}")
    print("Creating async resolver (headless=False)...")
    print("Chrome should open in a visible window\n")
    
    # Configurar logger
    logger = get_logger()
    logger.clear()
    
    def log_callback(level, message):
        print(f"[{level}] {message}")
    
    logger.register_callback(log_callback)
    
    try:
        # Crear resolver async
        resolver = AsyncLinkResolver(headless=False)
        print("OK - AsyncResolver created successfully!\n")
        
        print("Starting async resolution...\n")
        
        # Resolver
        result = await resolver.resolve(
            url=test_url,
            quality="1080p",
            format_type="WEB-DL",
            providers=["utorrent", "drive.google"],
            language="latino"
        )
        
        print("\n" + "=" * 70)
        if result and result.url != "LINK_NOT_RESOLVED":
            print("[SUCCESS]")
            print(f"URL: {result.url}")
            print(f"Provider: {result.provider}")
            print(f"Quality: {result.quality}")
            print(f"Score: {result.score}")
        else:
            print("[FAILED] - No result returned")
        print("=" * 70)
        
        return result
        
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
        return None

# Ejecutar
if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print(f"Running on: {sys.platform}")
    print(f"Event loop policy: {asyncio.get_event_loop_policy()}\n")
    
    result = asyncio.run(main())
    
    print("\n" + "=" * 70)
    if result:
        print("[SUCCESS] AsyncLinkResolver works correctly!")
        print("The GUI should now work properly.")
    else:
        print("[FAILED] Test failed")
    print("=" * 70)

"""
Test que verifica que Playwright funciona con ProactorEventLoopPolicy en un executor
Esto simula exactamente el flujo de la GUI
"""
import sys
import os
import asyncio

# Configurar Proactor Event Loop Policy (como lo hace la GUI ahora)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("[OK] Set to ProactorEventLoopPolicy")

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from resolver import LinkResolver
from logger import get_logger

print("=" * 70)
print("Testing LinkResolver with ProactorEventLoopPolicy in executor")
print("=" * 70)

test_url = "https://www.peliculasgd.net/pelicula/eragon/"

# Configurar logger
logger = get_logger()
logger.clear()

logs = []
def log_callback(level, message):
    log_line = f"[{level}] {message}"
    logs.append(log_line)
    print(log_line)

logger.register_callback(log_callback)

# Función que simula el flujo de la GUI
def run_resolver():
    """Ejecuta el resolver (síncronamente, pero dentro de un thread del executor)"""
    print("\n[THREAD] Creating LinkResolver...")
    resolver = LinkResolver(headless=False)
    print("[THREAD] Resolver created!")
    
    print("[THREAD] Starting resolution...")
    result = resolver.resolve(
        url=test_url,
        quality="1080p",
        format_type="WEB-DL",
        providers=["utorrent", "drive.google"],
        language="latino"
    )
    print("[THREAD] Resolution completed!")
    
    return result

# Función async principal
async def main():
    """Simula el flujo async de la GUI"""
    print("\n" + "=" * 70)
    print("Starting async executor (like GUI does)...")
    print("=" * 70 + "\n")
    
    try:
        # Ejecutar en executor igual que la GUI
        result = await asyncio.get_event_loop().run_in_executor(
            None, run_resolver
        )
        
        print("\n" + "=" * 70)
        print("RESULT:")
        if result and result.url != "LINK_NOT_RESOLVED":
            print("[SUCCESS]")
            print(f"  URL: {result.url[:80]}")
            print(f"  Provider: {result.provider}")
            print(f"  Quality: {result.quality}")
            print(f"  Score: {result.score}")
        else:
            print("[FAILED] - No result returned")
        print("=" * 70)
        
        return result
        
    except Exception as e:
        print(f"\n[ERROR] in async flow: {e}")
        import traceback
        traceback.print_exc()
        return None

# Ejecutar
if __name__ == "__main__":
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Event loop policy: {asyncio.get_event_loop_policy()}\n")
    
    result = asyncio.run(main())
    
    print("\n" + "=" * 70)
    if result:
        print("[SUCCESS] Test PASSED!")
        print("The GUI should now work correctly.")
        print("\nChrome should have opened during the test.")
    else:
        print("[FAILED] Test failed")
    print("=" * 70)

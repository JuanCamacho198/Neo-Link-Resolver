"""
Test que simula el flujo exacto de la GUI para diagnosticar el problema
"""
import sys
import os
import asyncio

# Fix para Windows
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception as e:
        print(f"Warning: Could not set event loop policy: {e}")

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from resolver import LinkResolver
from logger import get_logger

print("=" * 70)
print("Testing GUI Flow - Async Executor Simulation")
print("=" * 70)

# URL de prueba
test_url = "https://www.peliculasgd.net/pelicula/eragon/"

# Logs capturados
logs = []

def log_callback(level, message):
    """Callback para capturar logs"""
    log_line = f"[{level}] {message}"
    logs.append(log_line)
    print(log_line)

# Función que simula run_resolver() de la GUI
def run_resolver():
    """Simula la función run_resolver de la GUI"""
    logger = get_logger()
    logger.clear()
    logger.register_callback(log_callback)
    
    try:
        print("\n>>> Creating LinkResolver...")
        resolver = LinkResolver(headless=False)
        print(">>> Resolver created!")
        
        print(">>> Starting resolution...")
        result = resolver.resolve(
            url=test_url,
            quality="1080p",
            format_type="WEB-DL",
            providers=["utorrent", "drive.google"],
            language="latino"
        )
        print(">>> Resolution completed!")
        
        return result
    except Exception as e:
        print(f"\n>>> ERROR in run_resolver: {e}")
        import traceback
        traceback.print_exc()
        return None

# Función async que simula resolve_link() de la GUI
async def simulate_gui_flow():
    """Simula el flujo async de la GUI"""
    print("\n" + "=" * 70)
    print("Starting async executor (like GUI does)...")
    print("=" * 70 + "\n")
    
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, run_resolver
        )
        
        print("\n" + "=" * 70)
        print("RESULT:")
        if result:
            print(f"✅ SUCCESS!")
            print(f"  URL: {result.url}")
            print(f"  Provider: {result.provider}")
            print(f"  Quality: {result.quality}")
            print(f"  Score: {result.score}")
        else:
            print("❌ FAILED - No result returned")
        print("=" * 70)
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERROR in async flow: {e}")
        import traceback
        traceback.print_exc()
        return None

# Ejecutar
if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print(f"Running on: {sys.platform}\n")
    
    # Ejecutar el flujo async
    result = asyncio.run(simulate_gui_flow())
    
    print("\n" + "=" * 70)
    print("TEST COMPLETED")
    print("=" * 70)
    print(f"\nCaptured {len(logs)} log messages")
    
    if result:
        print("\n✅ Test PASSED - Resolver works from async executor")
    else:
        print("\n❌ Test FAILED - Resolver returned None")
        print("\nLast 10 logs:")
        for log in logs[-10:]:
            print(f"  {log}")

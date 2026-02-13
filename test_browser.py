"""
Test simple para verificar si Playwright puede abrir Chrome
"""
from playwright.sync_api import sync_playwright
import sys

print("Testing Playwright browser launch...")
print(f"Python: {sys.version}")

try:
    with sync_playwright() as p:
        print("✓ Playwright imported successfully")
        
        # Intentar lanzar navegador
        print("Launching browser (visible)...")
        browser = p.chromium.launch(headless=False)
        print("✓ Browser launched successfully!")
        
        # Crear página
        page = browser.new_page()
        print("✓ Page created")
        
        # Navegar a ejemplo
        page.goto("https://www.google.com")
        print("✓ Navigation successful")
        
        # Esperar un poco
        import time
        time.sleep(3)
        
        # Cerrar
        browser.close()
        print("✓ Browser closed")
        
        print("\n🎉 All tests passed! Chrome should work correctly.")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    print("\nPossible solutions:")
    print("1. Run: python -m playwright install chromium")
    print("2. Run: python -m playwright install chromium --with-deps")

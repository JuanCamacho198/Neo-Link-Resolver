from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        # Lanzamos el navegador en modo 'headed' (visible) para ver qué pasa
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("🕶️ Neo-Link Agent v0.1: Connecting to the Matrix...")
        
        target_url = "https://www.peliculasgd.net/"
        print(f"🌍 Navigating to: {target_url}")
        
        try:
            page.goto(target_url, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            print("📸 Taking surveillance photo...")
            page.screenshot(path="surveillance_entry.png")
            print("✅ Page loaded. Check 'surveillance_entry.png'")
            
            # Aquí irá la lógica de búsqueda de películas
            # Por ahora, solo mantenemos el navegador abierto unos segundos
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ Glitch in the Matrix: {e}")
        
        finally:
            browser.close()
            print("🚪 Exiting the Matrix.")

if __name__ == "__main__":
    run()

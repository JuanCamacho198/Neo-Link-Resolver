
import os
import time
import sys
from playwright.sync_api import sync_playwright

# Añadir src al path para usar tus herramientas existentes
sys.path.append(os.path.join(os.getcwd(), 'src'))
try:
    from stealth_config import apply_stealth_to_page, STEALTH_AVAILABLE
except ImportError:
    STEALTH_AVAILABLE = False
    print("Warning: stealth_config not found in src/")

PROFILE_PATH = os.path.join(os.getcwd(), "data", "browser_profile")

def debug_browser():
    with sync_playwright() as p:
        print(f"Launching browser with profile: {PROFILE_PATH}")
        
        # Intentamos usar el perfil persistente. 
        # Si falla porque el navegador está abierto, se lo diremos al usuario.
        try:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_PATH,
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                ]
            )
        except Exception as e:
            print(f"Error al lanzar el navegador: {e}")
            print("ASEGÚRATE DE QUE CHROME ESTÉ CERRADO.")
            return

        page = browser.pages[0] if browser.pages else browser.new_page()
        
        if STEALTH_AVAILABLE:
            apply_stealth_to_page(page)
            print("✓ Stealth mode applied")

        # Intentar llegar a la URL que el usuario mencionó
        target_url = "https://neworldtravel.com/"
        print(f"Navegando a: {target_url}")
        
        try:
            page.goto(target_url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Timeout o error al cargar: {e}")

        # Crear carpeta de capturas
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

        # Bucle de interacción para depurar pasos
        for step in range(1, 4):
            print(f"\n--- Paso {step} ---")
            time.sleep(5) # Esperar a que carguen botones/scripts
            
            current_url = page.url
            filename = f"screenshots/neworld_step_{step}.png"
            page.screenshot(path=filename)
            print(f"URL: {current_url}")
            print(f"Captura guardada en: {filename}")
            
            # Buscar botones típicos de acortadores
            # Estos selectores son comunes en acortadores similares
            selectors = [
                "button:has-text('Continuar')", 
                "a:has-text('Continuar')",
                "#continue-button",
                ".btn-success",
                "button:has-text('Get Link')",
                "a:has-text('Get Link')"
            ]
            
            found = False
            for selector in selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=2000)
                    if element and element.is_visible():
                        print(f"Botón encontrado: {selector}. Haciendo click...")
                        element.click()
                        found = True
                        break
                except:
                    continue
            
            if not found:
                print("No se encontró ningún botón obvio. Esperando intervención manual o scripts...")
                # Aquí podrías intentar ejecutar un script para saltar el timer si existiera
            
            if "google.com" in page.url or "mega.nz" in page.url or "drive.google" in page.url:
                print(f"¡URL final detectada!: {page.url}")
                break

        print("\nDepuración terminada. El navegador se cerrará en 10 segundos.")
        time.sleep(10)
        browser.close()

if __name__ == "__main__":
    debug_browser()

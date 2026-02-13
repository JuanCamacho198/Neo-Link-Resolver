
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
        print("Launching browser WITHOUT profile for clean test")
        
        try:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                ]
            )
            # User agent realista para evitar bloqueos inmediatos
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            context = browser.new_context(user_agent=user_agent)
        except Exception as e:
            print(f"Error al lanzar el navegador: {e}")
            return

        page = context.new_page()
        
        # Aplicamos evasiones manuales y de librería
        from stealth_config import apply_stealth_to_context
        apply_stealth_to_context(context)
        print("✓ Manual stealth evasions applied to context")

        if STEALTH_AVAILABLE:
            try:
                apply_stealth_to_page(page)
                print("✓ Library stealth mode applied to page")
            except Exception as e:
                print(f"⚠ Could not apply library stealth: {e}")

        # Intentar llegar a la URL que el usuario mencionó (usando un ejemplo real de r.php si es posible)
        target_url = "https://neworldtravel.com/r.php?f=UTZBWWJQaVQ4eUlr"
        print(f"Navegando a: {target_url}")
        
        try:
            # Intentar con referer de PeliculasGD
            page.goto(target_url, wait_until="networkidle", timeout=60000, referer="https://www.peliculasgd.net/")
        except Exception as e:
            print(f"Timeout o error al cargar: {e}")

        # Bucle de interacción para depurar pasos
        for step in range(1, 6):
            print(f"\n--- Paso {step} ---")
            time.sleep(5) 
            
            current_url = page.url
            print(f"URL actual: {current_url}")
            
            # 1. Buscar en Frames
            print(f"Detectados {len(page.frames)} frames.")
            
            # 2. Buscar el elemento específico mencionado por el usuario en todos los frames
            found_element = None
            for frame in page.frames:
                try:
                    # Buscar el div con clase text que contiene Continuar
                    el = frame.query_selector("div.text:has-text('Continuar')")
                    if el and el.is_visible():
                        print(f"¡ENCONTRADO! Div con clase 'text' en frame: {frame.url}")
                        found_element = el
                        break
                except:
                    continue
            
            if found_element:
                print("Intentando clickear el elemento encontrado...")
                found_element.click()
                time.sleep(2)
                continue

            # 3. Fallback a los otros selectores
            selectors = [
                "div.text:has-text('Continuar')",
                "div:has-text('Continuar al enlace')",
                "button:has-text('Continuar')", 
                "a:has-text('Continuar')",
                "button:has-text('Get Link')",
                "a:has-text('Get Link')"
            ]
            
            found = False
            for selector in selectors:
                for frame in page.frames:
                    try:
                        element = frame.wait_for_selector(selector, timeout=1000)
                        if element and element.is_visible():
                            print(f"Botón encontrado ({selector}) en frame {frame.name or frame.url}. Click...")
                            element.click()
                            found = True
                            break
                    except:
                        continue
                if found: break
            
            if not found:
                print("No se detectó botón interactivo. Tomando captura...")
                page.screenshot(path=f"screenshots/neworld_step_{step}.png")
            
            if "google.com" in page.url and "zx=" in page.url:
                print("Detección de bot confirmada (redirigido a Google con zx= parameter)")
                # Intentar volver atrás y esperar?
                # page.go_back()
                # time.sleep(5)
            
            if "mega.nz" in page.url or "drive.google" in page.url:
                print(f"¡URL FINAL LOGRADA!: {page.url}")
                break

        print("\nDepuración terminada. El navegador se cerrará en 10 segundos.")
        time.sleep(10)
        browser.close()

if __name__ == "__main__":
    debug_browser()

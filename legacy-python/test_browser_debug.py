
import os
import time
import sys
import psutil
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
    import psutil
    
    # Verificar si Chrome está abierto
    chrome_running = any("chrome" in p.name().lower() for p in psutil.process_iter())
    if chrome_running:
        print("⚠️  Chrome está abierto. Ciérralo completamente antes de continuar.")
        print("   Presiona Ctrl+C para cancelar y cerrar Chrome.")
        try:
            time.sleep(10)  # Dar tiempo para cerrar
        except KeyboardInterrupt:
            print("Cancelado.")
            return
    
    with sync_playwright() as p:
        print("Launching browser WITH profile for session persistence")
        
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
            print("Asegúrate de que Chrome esté completamente cerrado.")
            return

        page = browser.pages[0] if browser.pages else browser.new_page()
        
        # Aplicamos evasiones manuales y de librería
        from stealth_config import apply_stealth_to_context
        apply_stealth_to_context(browser)
        print("✓ Manual stealth evasions applied to context")

        if STEALTH_AVAILABLE:
            try:
                apply_stealth_to_page(page)
                print("✓ Library stealth mode applied to page")
            except Exception as e:
                print(f"⚠ Could not apply library stealth: {e}")

        # Fase 6: Human-in-the-loop desde el inicio
        print("🔄 Modo human-in-the-loop activado")
        print("1. El navegador se abrirá en blanco.")
        print("2. Navega manualmente a: https://neworldtravel.com/r.php?f=UTZBWWJQaVQ4eUlr")
        print("3. Resuelve cualquier captcha o challenge que aparezca.")
        print("4. Una vez que veas el botón 'Continuar al enlace', presiona Enter aquí para continuar.")
        
        # Esperar hasta que esté en la URL correcta
        print("Esperando que navegues a NewWorldTravel...")
        while True:
            current_url = page.url
            if "neworldtravel.com" in current_url:
                print(f"✓ Detectado en NewWorldTravel: {current_url}")
                break
            time.sleep(2)
            print(f"URL actual: {current_url} (esperando neworldtravel.com...)")
        
        input("Presiona Enter cuando el botón 'Continuar al enlace' esté visible...")

        # Ahora verificar la URL actual
        current_url = page.url
        print(f"URL actual después de navegación manual: {current_url}")

        if "google.com" in current_url and "zx=" in current_url:
            print("🚨 Aún redirigido a Google. Intenta de nuevo o usa VPN/proxy.")
            browser.close()
            return

        # Inyectar aceleración de timers
        page.evaluate("""
            const originalSetTimeout = window.setTimeout;
            window.setTimeout = function(callback, delay) {
                return originalSetTimeout(callback, Math.min(delay, 100));
            };
            const originalSetInterval = window.setInterval;
            window.setInterval = function(callback, delay) {
                return originalSetInterval(callback, Math.min(delay, 100));
            };
            if (typeof counter !== 'undefined') counter = 0;
            if (typeof countdown !== 'undefined') countdown = 0;
        """)
        print("✓ Timer acceleration injected")

        # Bucle de interacción automática
        for step in range(1, 6):
            print(f"\n--- Paso {step} ---")
            time.sleep(1)  # Reducido, ya que esperamos condiciones arriba
            
            current_url = page.url
            print(f"URL actual: {current_url}")
            
            # Fase 1: Instrumentación detallada
            print(f"Frames totales: {len(page.frames)}")
            ready_state = page.evaluate("document.readyState")
            print(f"ReadyState: {ready_state}")
            
            # Buscar el div.text específico en TODAS las pestañas y frames
            target_selector = "div.text:has-text('Continuar al enlace')"
            found = False
            for p in browser.pages:
                if p.is_closed(): continue
                for frame in p.frames:
                    try:
                        elements = frame.query_selector_all(target_selector)
                        if elements:
                            for el in elements:
                                # Verificar visibilidad y posición
                                is_visible = el.is_visible()
                                bbox = el.bounding_box()
                                print(f"✓ Elemento encontrado en {p.url} (frame: {frame.name or 'main'}): visible={is_visible}, bbox={bbox}")
                                
                                if is_visible and bbox:
                                    print(f"🎯 Intentando click humano en {bbox}")
                                    try:
                                        # Mover el mouse al centro del botón
                                        center_x = bbox['x'] + bbox['width'] / 2
                                        center_y = bbox['y'] + bbox['height'] / 2
                                        
                                        p.mouse.move(center_x, center_y, steps=10)
                                        time.sleep(0.2)
                                        
                                        # Click "sucio" (down y up separados)
                                        p.mouse.down()
                                        time.sleep(0.1)
                                        p.mouse.up()
                                        
                                        print("✓ Click humano (mouse.move + down/up) enviado")
                                        
                                        # Si el click falló, intentar forzar vía evaluate
                                        time.sleep(1)
                                        if p.url == current_url:
                                            print("⚠ URL no cambió, forzando click vía script...")
                                            el.evaluate("el => { el.click(); el.dispatchEvent(new Event('click', {bubbles:true})); }")
                                        
                                        found = True
                                        break
                                    except Exception as e:
                                        print(f"⚠ Fallo click humano: {e}")
                                else:
                                    print(f"✗ Elemento no visible o sin bbox")
                    except Exception as e:
                        print(f"Error buscando en frame {frame.name}: {e}")
                if found: break
            
            if not found:
                print("✗ No se encontró el botón 'Continuar al enlace' en ninguna pestaña/frame")
            
            # Verificar si cambió la URL (posible redirección)
            new_url = page.url
            if new_url != current_url:
                print(f"⚡ URL cambió: {new_url}")
                if "google.com" in new_url and "zx=" in new_url:
                    print("🚨 Detectado bloqueo: redirección a Google con zx (bot challenge)")
                    print("🔄 Activando modo human-in-the-loop: resuelve manualmente el challenge en los próximos 60 segundos...")
                    print("   (Ej: completa el captcha, espera el timer, etc.)")
                    time.sleep(60)  # Dar tiempo al usuario para resolver manualmente
                    # Después del tiempo, continuar el bucle para ver si ya pasó
                    continue
                elif "drive.google.com" in new_url or "mega.nz" in new_url:
                    print("🎉 ¡URL final detectada!")
                    break
            
            # Tomar screenshot en cada paso
            if not os.path.exists("screenshots"):
                os.makedirs("screenshots")
            filename = f"screenshots/neworld_step_{step}.png"
            page.screenshot(path=filename)
            print(f"Captura guardada: {filename}")

        print("\nDepuración terminada. El navegador se cerrará en 10 segundos.")
        time.sleep(10)
        browser.close()

if __name__ == "__main__":
    debug_browser()

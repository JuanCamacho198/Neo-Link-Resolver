from playwright.sync_api import sync_playwright
import os

def dump_hackstore():
    url = "https://hackstore.mx/peliculas/zootopia-2-2025"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        print(f"Opening {url}...")
        page.goto(url)
        page.wait_for_load_state("networkidle")
        
        # Intentar click en ver enlaces y botones de descargar
        try:
            buttons = page.query_selector_all("button:has-text('Descargar'), button:has-text('VER ENLACES')")
            print(f"Encontrados {len(buttons)} botones de descarga.")
            for i, btn in enumerate(buttons):
                print(f"Clicking button {i}...")
                try:
                    btn.click()
                    page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"Error clicando botón {i}: {e}")
            
            # Esperar un poco más para que carguen los links dinámicos
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Error general buscando botones: {e}")
            
        content = page.content()
        with open("data/hackstore_debug.html", "w", encoding="utf-8") as f:
            f.write(content)
        print(f"HTML saved to data/hackstore_debug.html ({len(content)} bytes)")
        browser.close()

if __name__ == "__main__":
    dump_hackstore()

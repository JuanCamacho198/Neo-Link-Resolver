import sys
import os
import time
from playwright.sync_api import sync_playwright

# Añadir src al path
sys.path.append(os.path.join(os.getcwd(), 'src'))

def test_direct():
    url = "https://www.peliculasgd.net/bob-esponja-en-busca-de-los-pantalones-cuadrados-2025-web-dl-1080p-latino-googledrive/"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        
        print(f"[*] Navigating to {url}")
        page.goto(url)
        
        print("[*] STEP 1: Click Enlaces Publicos")
        page.wait_for_timeout(3000)
        btn1 = page.wait_for_selector("a:has(img[src*='cxx'])")
        btn1.click()
        
        print("[*] Waiting for step 2...")
        time.sleep(5)
        
        # Monitorizar todas las pestañas
        found_final = False
        start = time.time()
        while time.time() - start < 300:
            for p_active in context.pages:
                try:
                    p_url = p_active.url
                    if "domk5.net" in p_url or "drive.google" in p_url:
                        print(f"[!!!] SUCCESS: {p_url}")
                        found_final = True
                        break
                    
                    # Si vemos el botón AQUI, clic
                    btn_aqui = p_active.query_selector("a:has-text('AQUI')")
                    if btn_aqui:
                        print(f"[*] Found 'AQUI' in {p_url[:40]}. Clicking...")
                        btn_aqui.click()
                        time.sleep(2)
                        
                    # Si vemos el botón 'Continuar' en saboresmexico
                    if "saboresmexico" in p_url:
                        btn_cont = p_active.query_selector("a:has-text('Ingresa'), a:has-text('link'), a:has-text('Vínculo')")
                        if btn_cont:
                            print("[*] Found final button in blog! Clicking...")
                            btn_cont.click()
                            time.sleep(2)
                except: continue
            if found_final: break
            time.sleep(5)
            print(f"[*] Still waiting... {int(time.time() - start)}s | Tabs: {len(context.pages)}")

        browser.close()

if __name__ == "__main__":
    test_direct()

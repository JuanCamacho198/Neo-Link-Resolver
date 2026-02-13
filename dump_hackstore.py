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
        
        # Intentar click en ver enlaces
        try:
            btn = page.query_selector("button:has-text('VER ENLACES')")
            if btn:
                print("Clicking 'VER ENLACES'...")
                btn.click()
                page.wait_for_timeout(2000)
        except:
            pass
            
        content = page.content()
        with open("data/hackstore_debug.html", "w", encoding="utf-8") as f:
            f.write(content)
        print(f"HTML saved to data/hackstore_debug.html ({len(content)} bytes)")
        browser.close()

if __name__ == "__main__":
    dump_hackstore()

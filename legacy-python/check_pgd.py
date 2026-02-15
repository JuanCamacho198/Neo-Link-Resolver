from playwright.sync_api import sync_playwright
import sys
import os

def check_link():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        url = "https://www.peliculasgd.net/bob-esponja-en-busca-de-los-pantalones-cuadrados-2025-web-dl-1080p-latino-googledrive/"
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        
        el = page.query_selector("a:has(img.wp-image-125438)")
        if el:
            print(f"Href: {el.get_attribute('href')}")
            print(f"Outer HTML: {page.evaluate('el => el.outerHTML', el)}")
        else:
            print("Link not found")
        browser.close()

if __name__ == "__main__":
    check_link()

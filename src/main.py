"""
Neo-Link-Resolver v0.2 - The Full Pipeline
Navega desde una pagina de pelicula en peliculasgd.net hasta el link final,
atravesando multiples redirects, anti-bots y anuncios obligatorios.
"""

from playwright.sync_api import sync_playwright, expect, Page, BrowserContext
from human_sim import simulate_human_behavior, random_delay, human_mouse_move
import time
import sys

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_URL = (
    "https://www.peliculasgd.net/"
    "bob-esponja-en-busca-de-los-pantalones-cuadrados-2025-web-dl-1080p-latino-googledrive/"
)
TIMEOUT_NAV = 60_000       # 60s para navegaciones
TIMEOUT_ELEMENT = 15_000   # 15s para esperar elementos
AD_WAIT_SECONDS = 45       # Espera despues de click en anuncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def log(step: str, msg: str):
    print(f"  [{step}] {msg}")


def wait_for_new_page(context: BrowserContext, trigger_action, timeout=30_000) -> Page:
    """
    Ejecuta trigger_action (que deberia abrir una nueva pestana)
    y retorna la nueva Page que se abrio.
    """
    with context.expect_page(timeout=timeout) as new_page_info:
        trigger_action()
    new_page = new_page_info.value
    new_page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
    return new_page


def close_unwanted_popups(context: BrowserContext, keep_pages: list):
    """Cierra cualquier pestana que no este en la lista keep_pages."""
    for p in context.pages:
        if p not in keep_pages and not p.is_closed():
            url = p.url
            p.close()
            log("CLEANUP", f"Closed unwanted tab: {url[:60]}...")


# ---------------------------------------------------------------------------
# Step 1: Pagina de pelicula -> Click "Enlaces Publicos"
# ---------------------------------------------------------------------------
def step1_click_enlaces_publicos(page: Page, context: BrowserContext) -> Page:
    """
    En la pagina de la pelicula, busca la imagen de 'Enlaces Publicos'
    y hace click. Esto abre una nueva pestana (pagina intermedia 1).
    """
    log("STEP 1", "Looking for 'Enlaces Publicos' image link...")

    # La imagen tiene class wp-image-125438 o su src contiene "cxx"
    # El link esta envuelto en un <a> que contiene la imagen
    selectors = [
        "a:has(img.wp-image-125438)",
        "a:has(img[src*='cxx'])",
        "a:has(img[alt*='enlace' i])",
        "a:has(img[alt*='public' i])",
    ]

    link = None
    for sel in selectors:
        link = page.query_selector(sel)
        if link:
            log("STEP 1", f"Found with selector: {sel}")
            break

    if not link:
        # Fallback: buscar por texto cercano
        log("STEP 1", "Trying fallback: searching all images for 'cxx' pattern...")
        link = page.query_selector("img[src*='cxx']")
        if link:
            # Click en la imagen directamente, el <a> padre captura el evento
            pass

    if not link:
        raise Exception("Could not find 'Enlaces Publicos' link on the page")

    log("STEP 1", "Clicking 'Enlaces Publicos'...")
    random_delay(0.5, 1.5)

    new_page = wait_for_new_page(context, lambda: link.click())
    log("STEP 1", f"New tab opened: {new_page.url[:80]}...")
    return new_page


# ---------------------------------------------------------------------------
# Step 2: Pagina intermedia 1 -> Click "Haz clic aqui"
# ---------------------------------------------------------------------------
def step2_click_haz_clic_aqui(page: Page, context: BrowserContext) -> Page:
    """
    En la pagina intermedia (ej: neworldtravel.com),
    busca el div con texto 'Haz clic aqui' y clickea.
    Abre otra pestana.
    """
    log("STEP 2", f"On intermediate page: {page.url[:60]}...")
    log("STEP 2", "Looking for 'Haz clic aqui'...")

    page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
    random_delay(1.0, 3.0)

    # Buscar el div.text con "Haz clic aqui"
    selectors = [
        "div.text >> text='Haz clic aquí'",
        "div.text >> text='Haz clic aqui'",
        "text='Haz clic aquí'",
        "text='Haz clic aqui'",
    ]

    target = None
    for sel in selectors:
        try:
            target = page.wait_for_selector(sel, timeout=TIMEOUT_ELEMENT)
            if target:
                log("STEP 2", f"Found with: {sel}")
                break
        except Exception:
            continue

    if not target:
        raise Exception("Could not find 'Haz clic aqui' element")

    log("STEP 2", "Clicking 'Haz clic aqui'...")
    random_delay(0.5, 1.0)

    new_page = wait_for_new_page(context, lambda: target.click())
    log("STEP 2", f"New tab opened: {new_page.url[:80]}...")
    return new_page


# ---------------------------------------------------------------------------
# Step 3: Pagina intermedia 2 -> Click "CLIC AQUI PARA CONTINUAR"
# ---------------------------------------------------------------------------
def step3_click_continuar(page: Page, context: BrowserContext) -> Page:
    """
    En la segunda pagina intermedia (ej: saboresmexico.com),
    clickea el boton 'CLIC AQUI PARA CONTINUAR'.
    Abre una pestana de Google con resultados de busqueda.
    """
    log("STEP 3", f"On second intermediate: {page.url[:60]}...")
    log("STEP 3", "Looking for 'CLIC AQUI PARA CONTINUAR' button...")

    page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
    random_delay(1.0, 3.0)

    selectors = [
        "button.button-s:has-text('CLIC')",
        "button.button-s",
        "text='CLIC AQUÍ PARA CONTINUAR'",
        "text='CLIC AQUI PARA CONTINUAR'",
    ]

    button = None
    for sel in selectors:
        try:
            button = page.wait_for_selector(sel, timeout=TIMEOUT_ELEMENT)
            if button:
                log("STEP 3", f"Found with: {sel}")
                break
        except Exception:
            continue

    if not button:
        raise Exception("Could not find 'CLIC AQUI PARA CONTINUAR' button")

    log("STEP 3", "Clicking continue button...")
    random_delay(0.5, 1.5)

    new_page = wait_for_new_page(context, lambda: button.click())
    log("STEP 3", f"New tab opened (Google): {new_page.url[:80]}...")
    return new_page


# ---------------------------------------------------------------------------
# Step 4: Google -> Click primer resultado
# ---------------------------------------------------------------------------
def step4_click_first_google_result(page: Page, context: BrowserContext) -> Page:
    """
    En la pagina de resultados de Google, clickea el primer resultado.
    """
    log("STEP 4", "On Google search results...")
    log("STEP 4", f"URL: {page.url[:100]}...")

    page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
    random_delay(1.5, 3.0)

    # Selectores para el primer resultado de Google
    selectors = [
        "#search a[href]:not([href*='google'])",
        "#rso a[href]:not([href*='google'])",
        "div.g a[href]",
        "#search .yuRUbf a",
    ]

    first_result = None
    for sel in selectors:
        first_result = page.query_selector(sel)
        if first_result:
            log("STEP 4", f"Found first result with: {sel}")
            break

    if not first_result:
        raise Exception("Could not find first Google search result")

    href = first_result.get_attribute("href") or "unknown"
    log("STEP 4", f"First result URL: {href[:80]}...")
    log("STEP 4", "Clicking first result...")
    random_delay(0.5, 1.5)

    new_page = wait_for_new_page(context, lambda: first_result.click())
    log("STEP 4", f"Landed on: {new_page.url[:80]}...")
    return new_page


# ---------------------------------------------------------------------------
# Step 5: Verificacion humana -> Simular comportamiento + click Continuar
# ---------------------------------------------------------------------------
def step5_human_verification(page: Page):
    """
    La pagina pide verificar que eres humano:
    'Mueve el mouse, haz scroll, y haz clic en cualquier area'
    Luego click en boton 'Continuar' (con initSystem()).
    """
    log("STEP 5", "Human verification page...")
    log("STEP 5", "Simulating human behavior (mouse, scroll, clicks)...")

    page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
    random_delay(2.0, 4.0)

    # Simulacion intensa de comportamiento humano
    simulate_human_behavior(page, intensity="heavy")
    random_delay(2.0, 4.0)

    # Segunda ronda para ser mas convincente
    simulate_human_behavior(page, intensity="normal")
    random_delay(1.0, 3.0)

    # Buscar boton Continuar (el que tiene initSystem())
    log("STEP 5", "Looking for 'Continuar' button...")
    selectors = [
        "button.button-s:has-text('Continuar')",
        "button:has-text('Continuar')",
        "button.button-s",
    ]

    continuar_btn = None
    for sel in selectors:
        try:
            continuar_btn = page.wait_for_selector(sel, timeout=TIMEOUT_ELEMENT)
            if continuar_btn:
                log("STEP 5", f"Found 'Continuar' with: {sel}")
                break
        except Exception:
            continue

    if not continuar_btn:
        raise Exception("Could not find 'Continuar' button on verification page")

    log("STEP 5", "Clicking 'Continuar'...")
    random_delay(0.5, 1.5)
    continuar_btn.click()

    log("STEP 5", "Waiting for ad requirement to appear...")
    random_delay(2.0, 5.0)


# ---------------------------------------------------------------------------
# Step 6: Click en anuncio obligatorio + esperar 40s
# ---------------------------------------------------------------------------
def step6_click_ad_and_wait(page: Page, context: BrowserContext):
    """
    Aparece 'Haz clic en este anuncio para continuar' (#click_message).
    Hay que clickear el anuncio que aparece debajo y esperar ~40 segundos.
    """
    log("STEP 6", "Looking for mandatory ad click...")

    # Esperar a que aparezca el mensaje de anuncio
    try:
        page.wait_for_selector("#click_message", state="visible", timeout=TIMEOUT_ELEMENT)
        log("STEP 6", "Ad click message is visible.")
    except Exception:
        log("STEP 6", "Warning: #click_message not found, trying to continue anyway...")

    random_delay(1.0, 3.0)

    # El anuncio suele ser un iframe o un div debajo del mensaje
    # Intentar click en el area debajo del mensaje de anuncio
    ad_selectors = [
        "#click_message ~ *",          # Hermano siguiente del mensaje
        "iframe[src*='ad']",            # iframe de anuncio
        "ins.adsbygoogle",              # Google Ads
        "div[id*='ad']",               # Div con id que contenga 'ad'
        "#ad_container",
        ".ad-container",
    ]

    ad_clicked = False
    for sel in ad_selectors:
        ad = page.query_selector(sel)
        if ad and ad.is_visible():
            log("STEP 6", f"Found ad element with: {sel}")
            try:
                ad.click()
                ad_clicked = True
                log("STEP 6", "Clicked ad element.")
                break
            except Exception:
                continue

    if not ad_clicked:
        # Fallback: click en la zona inferior de la pagina donde suelen estar los ads
        log("STEP 6", "Fallback: clicking in ad zone (lower page area)...")
        viewport = page.viewport_size or {"width": 1280, "height": 720}
        page.mouse.click(viewport["width"] // 2, viewport["height"] - 150)

    # Cerrar cualquier popup/pestana que se haya abierto por el ad
    random_delay(2.0, 4.0)
    main_pages = [page]
    close_unwanted_popups(context, main_pages)

    log("STEP 6", f"Waiting {AD_WAIT_SECONDS} seconds for ad timer...")
    # Esperar con actividad humana ocasional para no parecer bot
    elapsed = 0
    while elapsed < AD_WAIT_SECONDS:
        chunk = min(10, AD_WAIT_SECONDS - elapsed)
        time.sleep(chunk)
        elapsed += chunk
        log("STEP 6", f"  ...{elapsed}/{AD_WAIT_SECONDS}s")
        if elapsed < AD_WAIT_SECONDS:
            human_mouse_move(page, steps=2)

    log("STEP 6", "Ad wait complete!")


# ---------------------------------------------------------------------------
# Step 7: Volver a pagina intermedia 1 para obtener el link final
# ---------------------------------------------------------------------------
def step7_return_to_intermediate(context: BrowserContext) -> str:
    """
    Despues de completar el circuito de anuncios, volvemos a la
    pagina intermedia 1 (tipo neworldtravel.com) donde ahora deberia
    estar disponible el link final.
    """
    log("STEP 7", "Returning to intermediate page for final link...")

    # Buscar la pestana intermedia entre las pestanas abiertas
    intermediate_page = None
    for p in context.pages:
        if p.is_closed():
            continue
        url = p.url.lower()
        # La pagina intermedia 1 no es Google, ni peliculasgd, ni saboresmexico
        if ("peliculasgd" not in url and
            "google" not in url and
            "saboresmexico" not in url and
            "about:blank" not in url):
            intermediate_page = p
            log("STEP 7", f"Found intermediate tab: {p.url[:80]}...")
            break

    if not intermediate_page:
        # Fallback: tomar la primera pestana que no sea blank
        for p in context.pages:
            if not p.is_closed() and "about:blank" not in p.url:
                intermediate_page = p
                break

    if not intermediate_page:
        raise Exception("Could not find intermediate page to return to")

    intermediate_page.bring_to_front()
    intermediate_page.reload(timeout=TIMEOUT_NAV)
    intermediate_page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAV)
    random_delay(2.0, 4.0)

    log("STEP 7", f"Back on: {intermediate_page.url}")

    # Intentar encontrar el link final
    link_selectors = [
        "a[href*='drive.google']",
        "a[href*='mega.nz']",
        "a[href*='mediafire']",
        "a[href*='1fichier']",
        "a[href*='download']",
        "a.btn",
        "a.button",
        "a:has-text('Download')",
        "a:has-text('Descargar')",
        "a:has-text('Enlace')",
    ]

    for sel in link_selectors:
        el = intermediate_page.query_selector(sel)
        if el:
            href = el.get_attribute("href")
            if href:
                log("STEP 7", f"FINAL LINK FOUND: {href}")
                return href

    # Si no se encuentra un link especifico, capturar todos los links
    log("STEP 7", "Specific link not found. Dumping all links on page...")
    all_links = intermediate_page.query_selector_all("a[href]")
    for a in all_links:
        href = a.get_attribute("href") or ""
        text = a.inner_text().strip()[:50] if a.inner_text() else ""
        if href and not href.startswith("#") and not href.startswith("javascript"):
            log("STEP 7", f"  Link: {text} -> {href[:100]}")

    # Tomar screenshot para debug
    intermediate_page.screenshot(path="final_page_debug.png")
    log("STEP 7", "Screenshot saved to 'final_page_debug.png' for manual inspection.")

    return "LINK_NOT_RESOLVED - check final_page_debug.png"


# ---------------------------------------------------------------------------
# Main: Orchestrate the full pipeline
# ---------------------------------------------------------------------------
def run(url: str = None):
    target_url = url or DEFAULT_URL

    print("=" * 60)
    print(" Neo-Link-Resolver v0.2 ")
    print(" 'There is no spoon... and there are no ads.' ")
    print("=" * 60)
    print(f"\nTarget: {target_url}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        # Pagina principal de la pelicula
        page = context.new_page()

        try:
            # -- Navigate to movie page --
            log("INIT", f"Opening {target_url[:60]}...")
            page.goto(target_url, timeout=TIMEOUT_NAV)
            page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAV)
            log("INIT", "Movie page loaded.")
            page.screenshot(path="step0_movie_page.png")

            # -- Step 1: Click "Enlaces Publicos" --
            intermediate_page1 = step1_click_enlaces_publicos(page, context)
            intermediate_page1.screenshot(path="step1_intermediate1.png")

            # -- Step 2: Click "Haz clic aqui" --
            intermediate_page2 = step2_click_haz_clic_aqui(intermediate_page1, context)
            intermediate_page2.screenshot(path="step2_intermediate2.png")

            # -- Step 3: Click "CLIC AQUI PARA CONTINUAR" --
            google_page = step3_click_continuar(intermediate_page2, context)
            google_page.screenshot(path="step3_google.png")

            # -- Step 4: Click first Google result --
            verification_page = step4_click_first_google_result(google_page, context)
            verification_page.screenshot(path="step4_verification.png")

            # -- Step 5: Human verification --
            step5_human_verification(verification_page)
            verification_page.screenshot(path="step5_after_continue.png")

            # -- Step 6: Click ad + wait --
            step6_click_ad_and_wait(verification_page, context)
            verification_page.screenshot(path="step6_after_ad.png")

            # -- Step 7: Return and get final link --
            final_link = step7_return_to_intermediate(context)

            print("\n" + "=" * 60)
            print(" RESULT")
            print("=" * 60)
            print(f" Final Link: {final_link}")
            print("=" * 60)

            # Mantener el navegador abierto un momento para verificar
            time.sleep(5)

        except Exception as e:
            print(f"\n  [ERROR] Glitch in the Matrix: {e}")
            # Screenshot de debug
            try:
                for i, p_tab in enumerate(context.pages):
                    if not p_tab.is_closed():
                        p_tab.screenshot(path=f"error_debug_tab{i}.png")
            except Exception:
                pass
            raise

        finally:
            browser.close()
            print("\n  [EXIT] Disconnected from the Matrix.")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else None
    run(url)

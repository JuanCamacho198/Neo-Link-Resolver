"""
human_sim.py - Simula comportamiento humano en el navegador.
Movimientos de mouse, scroll aleatorio, clicks en areas vacias, delays naturales.
"""

import random
import time


def random_delay(min_s=0.5, max_s=2.0):
    """Espera un tiempo aleatorio para simular velocidad humana."""
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def human_mouse_move(page, steps=5):
    """Mueve el mouse en trayectorias aleatorias por la pagina."""
    viewport = page.viewport_size
    if not viewport:
        viewport = {"width": 1280, "height": 720}

    for _ in range(steps):
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)
        page.mouse.move(x, y, steps=random.randint(5, 15))
        random_delay(0.2, 0.8)


def human_scroll(page, scrolls=3):
    """Hace scroll arriba/abajo de forma natural."""
    for _ in range(scrolls):
        direction = random.choice(["down", "up"])
        amount = random.randint(100, 400)
        if direction == "down":
            page.mouse.wheel(0, amount)
        else:
            page.mouse.wheel(0, -amount)
        random_delay(0.3, 1.0)


def human_click_empty(page, clicks=2):
    """Hace click en areas vacias de la pagina (no en links)."""
    viewport = page.viewport_size
    if not viewport:
        viewport = {"width": 1280, "height": 720}

    for _ in range(clicks):
        # Click en zonas "seguras" (margenes)
        x = random.randint(50, viewport["width"] - 50)
        y = random.randint(50, min(200, viewport["height"] - 50))
        page.mouse.click(x, y)
        random_delay(0.3, 0.7)


def simulate_human_behavior(page, intensity="normal"):
    """
    Ejecuta una secuencia completa de comportamiento humano.
    intensity: "light" | "normal" | "heavy"
    """
    configs = {
        "light":  {"moves": 2, "scrolls": 1, "clicks": 1},
        "normal": {"moves": 4, "scrolls": 3, "clicks": 2},
        "heavy":  {"moves": 8, "scrolls": 5, "clicks": 3},
    }
    cfg = configs.get(intensity, configs["normal"])

    print(f"    [SIM] Simulating human behavior ({intensity})...")
    human_mouse_move(page, steps=cfg["moves"])
    human_scroll(page, scrolls=cfg["scrolls"])
    human_click_empty(page, clicks=cfg["clicks"])
    random_delay(0.5, 1.5)
    print(f"    [SIM] Done.")

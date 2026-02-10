"""
screenshot_handler.py - Maneja la captura y envio de screenshots en tiempo real.
"""

import os
from datetime import datetime
from typing import Callable, Optional
from pathlib import Path


class ScreenshotHandler:
    """
    Captura screenshots del navegador y los envia a callbacks (GUI).
    """

    def __init__(self, output_dir: str = "screenshots", callback: Optional[Callable] = None):
        self.output_dir = output_dir
        self.callback = callback
        self.screenshot_count = 0
        
        # Crear directorio si no existe
        os.makedirs(output_dir, exist_ok=True)

    def set_callback(self, callback: Callable):
        """Registra un callback para recibir notificaciones de nuevos screenshots."""
        self.callback = callback

    def capture(self, page, name: str, description: str = "") -> str:
        """
        Captura un screenshot de la pagina actual.
        
        Args:
            page: Objeto Page de Playwright
            name: Nombre del screenshot (ej: "page_load", "link_found")
            description: Descripcion para mostrar en la GUI
            
        Returns:
            Path del screenshot capturado
        """
        try:
            self.screenshot_count += 1
            
            # Generar nombre de archivo con timestamp
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{self.screenshot_count:03d}_{name}_{timestamp}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            # Capturar screenshot
            page.screenshot(path=filepath)
            
            # Notificar al callback (GUI)
            if self.callback:
                try:
                    self.callback(
                        filepath=filepath,
                        name=name,
                        description=description,
                        url=page.url,
                    )
                except Exception as e:
                    print(f"Error in screenshot callback: {e}")
            
            return filepath
            
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None

    def capture_step(self, page, step: int, step_name: str) -> str:
        """Captura un screenshot de un paso especifico del proceso."""
        return self.capture(page, f"step{step}_{step_name}", f"Paso {step}: {step_name}")

    def clear(self):
        """Limpia los screenshots antiguos."""
        try:
            for file in Path(self.output_dir).glob("*.png"):
                file.unlink()
            self.screenshot_count = 0
        except Exception as e:
            print(f"Error clearing screenshots: {e}")

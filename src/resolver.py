"""
resolver.py - Wrapper del sistema de resolucion con logging integrado.
Interfaz simplificada para usar desde GUI o CLI.
"""

from typing import Optional
from playwright.sync_api import sync_playwright
from config import SearchCriteria
from adapters import get_adapter
from matcher import LinkOption
from logger import get_logger


class LinkResolver:
    """
    Wrapper del resolver que integra logging y manejo de errores.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.logger = get_logger()

    def resolve(
        self,
        url: str,
        quality: str = "1080p",
        format_type: str = "WEB-DL",
        providers: list = None,
        language: str = "latino",
    ) -> Optional[LinkOption]:
        """
        Resuelve un link con los criterios especificados.
        
        Returns:
            LinkOption con el mejor link encontrado, o None si falla.
        """
        if providers is None:
            providers = ["utorrent", "drive.google"]

        # Log inicio
        self.logger.info(f"Starting resolution for: {url[:80]}...")
        self.logger.info(f"Search criteria: {quality} {format_type} - Providers: {', '.join(providers)}")

        # Crear criterios
        criteria = SearchCriteria(
            quality=quality,
            format=format_type,
            preferred_providers=providers,
            language=language,
        )

        result = None

        try:
            with sync_playwright() as p:
                # Lanzar navegador
                self.logger.step("INIT", "Launching browser...")
                browser = p.chromium.launch(
                    headless=self.headless,
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

                try:
                    # Seleccionar adaptador
                    self.logger.step("ADAPTER", "Selecting site adapter...")
                    adapter = get_adapter(url, context, criteria)
                    self.logger.success(f"Using adapter: {adapter.name()}")

                    # Patchear el adaptador para que use nuestro logger
                    original_log = adapter.log
                    def patched_log(step, msg):
                        self.logger.step(step, msg)
                        original_log(step, msg)
                    adapter.log = patched_log

                    # Resolver
                    self.logger.step("RESOLVE", "Starting navigation...")
                    result = adapter.resolve(url)

                    if result:
                        self.logger.success("Link resolved successfully!")
                        self.logger.info(f"URL: {result.url}")
                        self.logger.info(f"Provider: {result.provider}")
                        self.logger.info(f"Quality: {result.quality or 'N/A'}")
                        self.logger.info(f"Format: {result.format or 'N/A'}")
                        self.logger.info(f"Score: {result.score:.1f}/100")
                    else:
                        self.logger.error("Could not resolve link")

                except ValueError as e:
                    self.logger.error(f"Unsupported site: {e}")
                except Exception as e:
                    self.logger.error(f"Resolution failed: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())

                finally:
                    browser.close()
                    self.logger.step("EXIT", "Browser closed")

        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        return result

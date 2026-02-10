"""
resolver.py - Wrapper del sistema de resolucion con logging integrado.
Interfaz simplificada para usar desde GUI o CLI.
"""

from typing import Optional, Callable
from playwright.sync_api import sync_playwright
from config import SearchCriteria
from adapters import get_adapter
from matcher import LinkOption
from logger import get_logger
from screenshot_handler import ScreenshotHandler
import time


class LinkResolver:
    """
    Wrapper del resolver que integra logging y manejo de errores.
    Incluye retry logic con backoff exponencial para recuperarse de fallos transitorios.
    """

    def __init__(self, headless: bool = True, screenshot_callback: Optional[Callable] = None, max_retries: int = 2):
        self.headless = headless
        self.logger = get_logger()
        self.screenshot_callback = screenshot_callback
        self.screenshot_handler = ScreenshotHandler(callback=screenshot_callback)
        self.max_retries = max_retries

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
        Implementa retry logic con exponential backoff.
        
        Returns:
            LinkOption con el mejor link encontrado, o None si falla.
        """
        # Intentar resolver con retry
        for attempt in range(self.max_retries + 1):
            try:
                result = self._resolve_internal(url, quality, format_type, providers, language)
                return result
            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    self.logger.warning(f"Resolution attempt {attempt + 1} failed: {str(e)[:80]}")
                    self.logger.info(f"Retrying after {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {self.max_retries + 1} resolution attempts failed")
                    return None
    
    def _resolve_internal(
        self,
        url: str,
        quality: str = "1080p",
        format_type: str = "WEB-DL",
        providers: list = None,
        language: str = "latino",
    ) -> Optional[LinkOption]:
        if providers is None:
            providers = ["utorrent", "drive.google"]

        # Validar input
        if not url or not isinstance(url, str):
            self.logger.error(f"Invalid URL provided: {url}")
            return None

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
        browser = None
        context = None

        try:
            with sync_playwright() as p:
                # Lanzar navegador
                try:
                    self.logger.step("INIT", "Launching browser...")
                    browser = p.chromium.launch(
                        headless=self.headless,
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--no-first-run",
                            "--no-default-browser-check",
                        ],
                    )
                except Exception as e:
                    self.logger.error(f"Failed to launch browser: {e}")
                    return None

                try:
                    context = browser.new_context(
                        viewport={"width": 1366, "height": 768},
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                    )
                except Exception as e:
                    self.logger.error(f"Failed to create browser context: {e}")
                    if browser:
                        browser.close()
                    return None

                try:
                    # Seleccionar adaptador
                    self.logger.step("ADAPTER", "Selecting site adapter...")
                    try:
                        adapter = get_adapter(url, context, criteria)
                        self.logger.success(f"Using adapter: {adapter.name()}")
                    except ValueError as e:
                        self.logger.error(f"Unsupported site: {e}")
                        return None

                    # Patchear el adaptador para que use nuestro logger
                    original_log = adapter.log
                    def patched_log(step, msg):
                        self.logger.step(step, msg)
                        original_log(step, msg)
                    adapter.log = patched_log

                    # Resolver
                    self.logger.step("RESOLVE", "Starting navigation...")
                    try:
                        result = adapter.resolve(url)
                    except Exception as e:
                        self.logger.error(f"Adapter resolution failed: {e}")
                        return None

                    if result:
                        self.logger.success("Link resolved successfully!")
                        self.logger.info(f"URL: {result.url}")
                        self.logger.info(f"Provider: {result.provider}")
                        self.logger.info(f"Quality: {result.quality or 'N/A'}")
                        self.logger.info(f"Format: {result.format or 'N/A'}")
                        self.logger.info(f"Score: {result.score:.1f}/100")
                    else:
                        self.logger.error("Adapter returned None - could not resolve link")

                except Exception as e:
                    self.logger.error(f"Unexpected error during resolution: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())

                finally:
                    # Cleanup
                    if context:
                        try:
                            context.close()
                        except Exception as e:
                            self.logger.warning(f"Error closing context: {e}")
                    
                    if browser:
                        try:
                            browser.close()
                            self.logger.step("EXIT", "Browser closed")
                        except Exception as e:
                            self.logger.warning(f"Error closing browser: {e}")

        except Exception as e:
            self.logger.error(f"Fatal error in resolve: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        return result

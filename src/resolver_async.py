"""
resolver_async.py - Version async del resolver para uso con GUI basadas en asyncio.
Soluciona el problema de NotImplementedError en Windows con WindowsSelectorEventLoopPolicy.
"""

from typing import Optional, Callable
from playwright.async_api import async_playwright
from config import SearchCriteria
from adapters import get_adapter
from matcher import LinkOption
from logger import get_logger
from screenshot_handler import ScreenshotHandler
from history_manager import HistoryManager
from network_analyzer import NetworkAnalyzer
from dom_analyzer import DOMAnalyzer
from timer_interceptor import TimerInterceptor
from stealth_config import apply_stealth_to_context, setup_popup_handler, STEALTH_AVAILABLE
from vision_fallback import VisionFallback
import time
import asyncio
import sys


class AsyncLinkResolver:
    """
    Version async del LinkResolver que funciona correctamente con event loops asyncio.
    Especialmente diseñado para GUIs que usan asyncio (NiceGUI, Streamlit, etc).
    """

    def __init__(self, headless: bool = True, screenshot_callback: Optional[Callable] = None, max_retries: int = 2):
        self.headless = headless
        self.logger = get_logger()
        self.screenshot_callback = screenshot_callback
        self.screenshot_handler = ScreenshotHandler(callback=screenshot_callback)
        self.max_retries = max_retries
        self.history_manager = HistoryManager()
        self.use_network_interception = True
        self.accelerate_timers = True
        self.use_vision_fallback = True

    async def resolve(
        self,
        url: str,
        quality: str = "1080p",
        format_type: str = "WEB-DL",
        providers: list = None,
        language: str = "latino",
    ) -> Optional[LinkOption]:
        """
        Resuelve un link de forma asincrona.
        """
        # Intentar resolver con retry
        for attempt in range(self.max_retries + 1):
            try:
                result = await self._resolve_internal(url, quality, format_type, providers, language)
                return result
            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Resolution attempt {attempt + 1} failed: {str(e)[:80]}")
                    self.logger.info(f"Retrying after {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"All {self.max_retries + 1} resolution attempts failed")
                    return None
    
    async def _resolve_internal(
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

        # Fix para Windows: cambiar temporalmente a ProactorEventLoopPolicy
        # ya que WindowsSelectorEventLoopPolicy no soporta subprocess
        old_policy = None
        if sys.platform == 'win32':
            try:
                old_policy = asyncio.get_event_loop_policy()
                if isinstance(old_policy, asyncio.WindowsSelectorEventLoopPolicy):
                    self.logger.info("Switching to ProactorEventLoopPolicy for Playwright...")
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception as e:
                self.logger.warning(f"Could not change event loop policy: {e}")

        try:
            async with async_playwright() as p:
                # Lanzar navegador
                try:
                    self.logger.step("INIT", "Launching browser...")
                    self.logger.info(f"Headless mode: {self.headless}")
                    browser = await p.chromium.launch(
                        headless=self.headless,
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--no-first-run",
                            "--no-default-browser-check",
                        ],
                    )
                    self.logger.success("Browser launched successfully!")
                except Exception as e:
                    self.logger.error(f"Failed to launch browser: {e}")
                    self.logger.error("Tip: Run 'python -m playwright install chromium' to install the browser")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    return None

                try:
                    context = await browser.new_context(
                        viewport={"width": 1366, "height": 768},
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                    )
                    
                    # Aplicar configuración anti-detección
                    if STEALTH_AVAILABLE:
                        self.logger.info("Applying stealth mode...")
                        apply_stealth_to_context(context)
                    
                    # Configurar manejo automático de popups
                    setup_popup_handler(context, auto_close=True)
                    
                except Exception as e:
                    self.logger.error(f"Failed to create browser context: {e}")
                    if browser:
                        await browser.close()
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
                    adapter.log = patched_log

                    # Configurar Network / DOM / Timer Analyzers
                    network_analyzer = NetworkAnalyzer()
                    dom_analyzer = DOMAnalyzer()
                    timer_interceptor = TimerInterceptor()
                    vision_fallback = VisionFallback() if self.use_vision_fallback else None
                    
                    adapter.set_analyzers(
                        network_analyzer=network_analyzer,
                        dom_analyzer=dom_analyzer,
                        timer_interceptor=timer_interceptor,
                        vision_resolver=vision_fallback
                    )

                    # Resolver (los adapters son síncronos, esto está OK)
                    self.logger.step("RESOLVE", "Starting navigation...")
                    try:
                        result = adapter.resolve(url)
                    except Exception as e:
                        self.logger.error(f"Adapter resolution failed: {e}")
                        return None

                    # Mostrar estadísticas
                    stats = network_analyzer.get_stats()
                    if stats['intercepted'] > 0:
                        self.logger.info(f"Network: {stats['blocked']} blocked ads")
                        self.logger.info(f"Captured: {stats['captured']} download candidates")

                    if result:
                        self.logger.success("Link resolved successfully!")
                        self.logger.info(f"URL: {result.url}")
                        self.logger.info(f"Provider: {result.provider}")
                        self.logger.info(f"Quality: {result.quality or 'N/A'}")
                        self.logger.info(f"Format: {result.format or 'N/A'}")
                        self.logger.info(f"Score: {result.score:.1f}/100")
                        
                        # Guardar en historial
                        self.history_manager.add_record(
                            original_url=url,
                            resolved_url=result.url,
                            quality=result.quality or "",
                            format_type=result.format or "",
                            provider=result.provider or "",
                            score=result.score
                        )
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
                            await context.close()
                        except Exception as e:
                            self.logger.warning(f"Error closing context: {e}")
                    
                    if browser:
                        try:
                            await browser.close()
                            self.logger.step("EXIT", "Browser closed")
                        except Exception as e:
                            self.logger.warning(f"Error closing browser: {e}")

        except Exception as e:
            self.logger.error(f"Fatal error in resolve: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        
        finally:
            # Restaurar el event loop policy original si se cambió
            if old_policy and sys.platform == 'win32':
                try:
                    self.logger.info("Restoring original event loop policy...")
                    asyncio.set_event_loop_policy(old_policy)
                except Exception as e:
                    self.logger.warning(f"Could not restore event loop policy: {e}")

        return result

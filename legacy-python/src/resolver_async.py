"""
resolver_async.py - Async bridge for the LinkResolver.
Uses ThreadPoolExecutor to run the sync resolver without blocking the event loop.
"""

import asyncio
from typing import Optional, List, Callable
from concurrent.futures import ThreadPoolExecutor
from .resolver import LinkResolver
from .matcher import LinkOption
from .logger import get_logger

class AsyncLinkResolver:
    """
    An async wrapper around the synchronous LinkResolver.
    This prevents mixing async/sync Playwright and ensures GUI stability.
    """
    def __init__(self, headless: bool = True, screenshot_callback: Optional[Callable] = None, max_retries: int = 1):
        self.headless = headless
        self.screenshot_callback = screenshot_callback
        self.max_retries = max_retries
        self._executor = ThreadPoolExecutor(max_workers=1)
        self.logger = get_logger()

    async def resolve(
        self,
        url: str,
        quality: str = "1080p",
        format_type: str = "WEB-DL",
        providers: Optional[List[str]] = None,
        language: str = "latino",
    ) -> Optional[LinkOption]:
        """Runs the sync resolver in a separate thread."""
        loop = asyncio.get_event_loop()
        
        # We pass the sync resolver call to the executor
        return await loop.run_in_executor(
            self._executor,
            self._sync_resolve_task,
            url,
            quality,
            format_type,
            providers,
            language
        )

    def _sync_resolve_task(
        self, 
        url: str, 
        quality: str, 
        format_type: str, 
        providers: List[str], 
        language: str
    ) -> Optional[LinkOption]:
        """The actual synchronous task running in the thread."""
        # Note: We create a NEW resolver instance per task to ensure clean state
        resolver = LinkResolver(
            headless=self.headless, 
            screenshot_callback=self.screenshot_callback,
            max_retries=self.max_retries
        )
        try:
            return resolver.resolve(
                url=url,
                quality=quality,
                format_type=format_type,
                providers=providers,
                language=language
            )
        except Exception as e:
            self.logger.error(f"AsyncBridge: Error in sync task: {e}")
            return None

    def __del__(self):
        self._executor.shutdown(wait=False)
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

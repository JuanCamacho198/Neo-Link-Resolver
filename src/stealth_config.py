"""
stealth_config.py - Configuración de evasión de detección con playwright-stealth.
"""

from playwright.sync_api import BrowserContext, Page
from logger import get_logger

try:
    from playwright_stealth import stealth_sync
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    stealth_sync = None

logger = get_logger()


def apply_stealth_to_page(page: Page) -> None:
    """
    Aplica técnicas de stealth a una página de Playwright para evitar detección de bots.
    """
    if not STEALTH_AVAILABLE:
        logger.warning("playwright-stealth not installed. Skipping stealth mode.")
        return
    
    try:
        stealth_sync(page)
        logger.debug("Stealth mode applied to page")
    except Exception as e:
        logger.warning(f"Failed to apply stealth mode: {e}")


def apply_stealth_to_context(context: BrowserContext) -> None:
    """
    Configura el contexto del navegador con headers y configuraciones anti-detección.
    """
    try:
        # Inyectar scripts adicionales para ocultar webdriver
        context.add_init_script("""
            // Sobrescribir la detección de webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Sobrescribir plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Sobrescribir languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'es']
            });
            
            // Chrome runtime
            window.chrome = {
                runtime: {}
            };
            
            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        logger.debug("Anti-detection scripts injected into context")
    except Exception as e:
        logger.warning(f"Failed to inject anti-detection scripts: {e}")


def setup_popup_handler(context: BrowserContext, auto_close: bool = True) -> None:
    """
    Configura el manejo automático de popups y pestañas no deseadas.
    
    Args:
        context: Contexto del navegador
        auto_close: Si True, cierra automáticamente popups de ads
    """
    if not auto_close:
        return
    
    def handle_popup(page: Page):
        """Maneja popups automáticamente."""
        try:
            url = page.url
            logger.debug(f"Popup detected: {url[:60]}")
            
            # Lista de dominios de ads/popups conocidos
            ad_patterns = [
                'doubleclick.net', 'googlesyndication.com', 'popads.net',
                'exoclick.com', 'adsterra.com', 'clickadu.com', 'propellerads.com',
                'juicyads.com', 'popcash.net', 'adf.ly', 'monetag.com',
                'about:blank'
            ]
            
            # Si es un ad conocido, cerrar inmediatamente
            if any(pattern in url.lower() for pattern in ad_patterns):
                logger.info(f"Auto-closing ad popup: {url[:60]}")
                page.close()
            else:
                # Si no es ad conocido, dejarlo abierto pero loggearlo
                logger.warning(f"Unknown popup opened (not auto-closed): {url[:60]}")
        except Exception as e:
            logger.debug(f"Error handling popup: {e}")
    
    # Registrar el handler
    context.on("page", handle_popup)
    logger.info("Popup auto-close handler registered")

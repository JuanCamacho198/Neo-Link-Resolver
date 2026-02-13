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
        logger.info("Stealth mode applied to page")
    except Exception as e:
        logger.warning(f"Failed to apply stealth mode: {e}")


def apply_stealth_to_context(context: BrowserContext) -> None:
    """
    Configura el contexto del navegador con headers y configuraciones anti-detección.
    """
    try:
        # Inyectar scripts adicionales para ocultar webdriver y otros fingerprints
        context.add_init_script("""
            // Sobrescribir la detección de webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Sobrescribir plugins con objetos realistas
            const makePlugin = (name, description, filename) => {
                const plugin = Object.create(Plugin.prototype);
                Object.defineProperties(plugin, {
                    name: { value: name },
                    description: { value: description },
                    filename: { value: filename },
                    length: { value: 0 }
                });
                return plugin;
            };
            const pluginsList = [
                makePlugin('Chrome PDF Viewer', 'Portable Document Format', 'internal-pdf-viewer'),
                makePlugin('Chromium PDF Viewer', 'Portable Document Format', 'internal-pdf-viewer'),
                makePlugin('Microsoft Edge PDF Viewer', 'Portable Document Format', 'internal-pdf-viewer'),
                makePlugin('PDF Viewer', 'Portable Document Format', 'internal-pdf-viewer'),
                makePlugin('WebKit built-in PDF', 'Portable Document Format', 'internal-pdf-viewer')
            ];
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const p = Object.create(PluginArray.prototype);
                    pluginsList.forEach((plugin, i) => p[i] = plugin);
                    Object.defineProperty(p, 'length', { get: () => pluginsList.length });
                    return p;
                }
            });

            // Canvas Fingerprinting Protection (Noise injection)
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                const ctx = this.getContext('2d');
                if (ctx) {
                    const imageData = ctx.getImageData(0, 0, this.width || 1, this.height || 1);
                    // Inyectar ruido imperceptible
                    for (let i = 0; i < 10; i++) {
                        const idx = Math.floor(Math.random() * imageData.data.length);
                        imageData.data[idx] = imageData.data[idx] ^ 1;
                    }
                    ctx.putImageData(imageData, 0, 0);
                }
                return originalToDataURL.apply(this, arguments);
            };

            // WebGL Noise
            const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                // UNMASKED_VENDOR_WEBGL = 0x9245, UNMASKED_RENDERER_WEBGL = 0x9246
                if (parameter === 0x9245) return 'Google Inc. (Intel)';
                if (parameter === 0x9246) return 'ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)';
                return originalGetParameter.apply(this, arguments);
            };
            
            // Sobrescribir languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'es']
            });
            
            // Chrome runtime
            window.chrome = {
                runtime: {
                    OnInstalledReason: { INSTALL: 'install', UPDATE: 'update', CHROME_UPDATE: 'chrome_update', SHARED_MODULE_UPDATE: 'shared_module_update' }
                }
            };
            
            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        logger.info("Anti-detection scripts (Stealth V2) injected into context")
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

    # Cargar dominios de ads desde el archivo de configuración
    ad_patterns = [
        'doubleclick.net', 'googlesyndication.com', 'popads.net',
        'exoclick.com', 'adsterra.com', 'clickadu.com', 'propellerads.com',
        'juicyads.com', 'popcash.net', 'adf.ly', 'monetag.com',
        'about:blank'
    ]
    
    import json
    import os
    config_path = "config/ad_domains.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                ad_patterns = list(set(ad_patterns + config.get('ad_domains', [])))
        except:
            pass
    
    def handle_popup(page: Page):
        """Maneja popups automáticamente."""
        try:
            # Esperar un poco a que la URL se estabilice
            page.wait_for_timeout(500)
            url = page.url
            
            # Si el popup es exactamente el mismo URL que la página principal, ignorar silenciosamente
            main_url = context.pages[0].url if context.pages else ""
            if url == main_url or url == main_url + "/":
                page.close()
                return

            logger.info(f"Popup detected: {url[:60]}")
            
            # Si es un ad conocido, cerrar inmediatamente
            if any(pattern in url.lower() for pattern in ad_patterns):
                logger.info(f"Auto-closing ad popup: {url[:60]}")
                page.close()
            else:
                # Si no es ad conocido, dejarlo abierto pero con log nivel bajo
                logger.debug(f"Unknown popup opened: {url[:60]}")
        except Exception as e:
            logger.debug(f"Error handling popup: {e}")
    
    # Registrar el handler
    context.on("page", handle_popup)
    logger.info(f"Popup auto-close handler registered ({len(ad_patterns)} patterns)")

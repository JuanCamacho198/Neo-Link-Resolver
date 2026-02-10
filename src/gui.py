"""
gui.py - Interfaz grafica moderna para Neo-Link-Resolver.

Ejecutar:
    python src/gui.py

Abre un navegador con la interfaz en http://localhost:8081
"""

from nicegui import ui, app
import asyncio
from typing import Optional, List, Dict
from resolver import LinkResolver
from logger import get_logger
from matcher import LinkOption
from quality_detector import QualityDetector


# =============================================================================
# Estado global de la aplicacion
# =============================================================================
class AppState:
    def __init__(self):
        self.resolver: Optional[LinkResolver] = None
        self.is_resolving: bool = False
        self.result: Optional[LinkOption] = None


state = AppState()


# =============================================================================
# Funciones de resolucion (async wrapper)
# =============================================================================
async def resolve_link(
    url: str,
    quality: str,
    format_type: str,
    providers: list,
    log_area,
    result_card,
    resolve_btn,
    spinner,
    screenshot_area,
):
    """
    Ejecuta la resolucion de forma asincrona y actualiza la UI.
    Incluye manejo robusto de errores.
    """
    state.is_resolving = True
    state.result = None
    resolve_btn.disable()
    spinner.set_visibility(True)

    # Limpiar areas
    log_area.clear()
    screenshot_area.clear()

    # Contador de screenshots para actualizar la UI
    screenshot_list = []

    # Callback para screenshots
    def screenshot_callback(filepath: str, name: str, description: str, url: str):
        """Recibe notificaciones de nuevos screenshots."""
        screenshot_list.append({
            "filepath": filepath,
            "name": name,
            "description": description,
            "url": url,
        })
        
        # Actualizar la UI con el ultimo screenshot
        screenshot_area.clear()
        with screenshot_area:
            with ui.row().classes('items-center gap-2 mb-2'):
                ui.label(f'Screenshot {len(screenshot_list)}').classes('text-bold text-primary')
                ui.label(f'({name})').classes('text-xs text-grey-7')
            
            try:
                # Mostrar imagen
                ui.image(filepath).classes('w-full max-h-96 object-contain rounded-lg border border-grey-5')
                ui.label(description).classes('text-xs text-grey-7 mt-2')
                ui.label(url[:80] + "...").classes('text-xs font-mono text-grey-7')
            except Exception as e:
                ui.label(f"Error loading image: {e}").classes('text-xs text-negative')

    # Callback para logs
    def log_callback(level: str, message: str):
        # Determinar color segun nivel
        color_map = {
            "INFO": "blue-grey-7",
            "SUCCESS": "positive",
            "WARNING": "warning",
            "ERROR": "negative",
            "STEP": "primary",
        }
        color = color_map.get(level, "grey-7")

        # Agregar log a la UI
        with log_area:
            ui.label(message).classes(f'text-{color} text-xs font-mono')

    # Registrar callbacks
    logger = get_logger()
    logger.clear()
    logger.register_callback(log_callback)

    # Ejecutar resolucion en thread separado (para no bloquear UI)
    def run_resolver():
        try:
            resolver = LinkResolver(headless=False, screenshot_callback=screenshot_callback)
            return resolver.resolve(url, quality, format_type, providers)
        except Exception as e:
            logger.log("ERROR", f"Resolver exception: {str(e)[:100]}")
            return None

    # Ejecutar en executor (thread pool)
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, run_resolver
        )
    except Exception as e:
        logger.log("ERROR", f"Task execution failed: {str(e)[:100]}")
        result = None

    # Actualizar resultado
    state.result = result
    state.is_resolving = False
    resolve_btn.enable()
    spinner.set_visibility(False)

    # Mostrar resultado
    result_card.clear()
    with result_card:
        try:
            if result and result.url != "LINK_NOT_RESOLVED":
                ui.label("Resolucion exitosa!").classes('text-h6 text-positive')
                ui.separator()
                
                # Link final (clickeable y copiable)
                ui.label("Link de descarga:").classes('text-bold mt-4')
                link_text = ui.input(
                    value=result.url,
                ).classes('w-full font-mono').props('outlined dense readonly')
                
                # Botones de accion
                with ui.row().classes('gap-2 mt-2'):
                    ui.button(
                        'Copiar Link',
                        icon='content_copy',
                        on_click=lambda: (
                            ui.run_javascript(f'navigator.clipboard.writeText("{result.url}")'),
                            ui.notify('Link copiado al portapapeles!', type='positive')
                        )
                    ).props('outline color=primary')
                    
                    ui.button(
                        'Abrir en navegador',
                        icon='open_in_new',
                        on_click=lambda: ui.run_javascript(f'window.open("{result.url}", "_blank")')
                    ).props('outline color=primary')

                # Detalles del resultado
                ui.separator().classes('my-4')
                ui.label("Detalles:").classes('text-bold')
                
                with ui.grid(columns=2).classes('gap-2 mt-2'):
                    ui.label("Proveedor:").classes('text-grey-7')
                    ui.label(result.provider or 'N/A').classes('text-bold')
                    
                    ui.label("Calidad:").classes('text-grey-7')
                    ui.label(result.quality or 'N/A').classes('text-bold')
                    
                    ui.label("Formato:").classes('text-grey-7')
                    ui.label(result.format or 'N/A').classes('text-bold')
                    
                    ui.label("Score:").classes('text-grey-7')
                    score_color = 'positive' if result.score >= 70 else 'warning' if result.score >= 40 else 'negative'
                    ui.label(f'{result.score:.1f}/100').classes(f'text-bold text-{score_color}')

            else:
                ui.label("No se pudo resolver el link").classes('text-h6 text-negative')
                ui.label("Revisa los logs para mas detalles.").classes('text-grey-7')
                if screenshot_list:
                    ui.label(f"Se capturaron {len(screenshot_list)} screenshots que puedes revisar en la seccion de visualizacion.").classes('text-xs text-warning mt-2')
        except Exception as e:
            ui.label("Error displaying results").classes('text-h6 text-negative')
            ui.label(f"Details: {str(e)[:100]}").classes('text-xs text-grey-7')


# =============================================================================
# Construccion de la UI
# =============================================================================
def build_ui():
    """Construye la interfaz completa con nuevo flujo: URL -> Detectar -> Resolver"""
    
    # Header
    with ui.header().classes('items-center justify-between bg-gradient-to-r from-indigo-500 to-purple-600'):
        with ui.row().classes('items-center gap-3'):
            ui.label('🕶️').classes('text-3xl')
            ui.label('Neo-Link-Resolver').classes('text-h5 text-white font-bold')
        ui.label('v0.4.1').classes('text-white text-sm')

    # Container principal
    with ui.column().classes('w-full max-w-6xl mx-auto p-6 gap-6'):
        
        # Descripcion
        with ui.card().classes('w-full'):
            ui.label('"There is no spoon... and there are no ads."').classes('text-italic text-grey-7')
            ui.label('Ingresa URL, detecta calidades, resuelve links automáticamente.').classes('text-sm mt-2')

        # ============================================================
        # PASO 1: URL + Detectar Calidades
        # ============================================================
        with ui.card().classes('w-full'):
            ui.label('Paso 1: URL y Detectar').classes('text-h6 mb-4')
            
            with ui.row().classes('w-full gap-2'):
                # URL input
                url_input = ui.input(
                    label='URL',
                    placeholder='https://hackstore.mx/peliculas/matrix-1999',
                ).classes('flex-grow').props('outlined clearable')
                
                # Spinner y boton detectar
                detect_spinner = ui.spinner(size='sm', color='primary')
                detect_spinner.set_visibility(False)
                
                detect_btn = ui.button(
                    'Detectar Calidades',
                    icon='auto_awesome',
                ).props('outline color=primary')

        # ============================================================
        # PASO 2: Seleccionar preferencias (oculto al inicio)
        # ============================================================
        config_card = ui.card().classes('w-full')
        config_card.set_visibility(False)
        
        with config_card:
            ui.label('Paso 2: Selecciona Preferencias').classes('text-h6 mb-4')
            
            # Grid de opciones
            with ui.grid(columns='1fr 1fr').classes('gap-4 w-full'):
                # Calidad
                quality_select = ui.select(
                    label='Calidad',
                    options=['1080p', '720p', '480p'],
                    value='1080p',
                ).classes('w-full').props('outlined')

                # Formato
                format_select = ui.select(
                    label='Formato',
                    options=['WEB-DL', 'BluRay', 'BRRip', 'HDRip', 'DVDRip', 'CAMRip'],
                    value='WEB-DL',
                ).classes('w-full').props('outlined')

            # Proveedores (multi-select)
            providers_select = ui.select(
                label='Proveedores preferidos',
                options={
                    'utorrent': 'uTorrent (Torrent)',
                    'drive.google': 'Google Drive',
                    'mega': 'Mega.nz',
                    'mediafire': 'MediaFire',
                    '1fichier': '1fichier',
                },
                value=['utorrent', 'drive.google'],
                multiple=True,
            ).classes('w-full mt-4').props('outlined')

            # Boton resolver
            with ui.row().classes('w-full justify-end gap-2 mt-6'):
                resolve_spinner = ui.spinner(size='sm', color='primary')
                resolve_spinner.set_visibility(False)
                
                resolve_btn = ui.button(
                    'Resolver Link',
                    icon='smart_toy',
                ).props('size=lg color=positive')

        # ============================================================
        # Area de visualizacion (screenshots)
        # ============================================================
        with ui.card().classes('w-full'):
            with ui.row().classes('items-center justify-between mb-2'):
                ui.label('Visualizacion en tiempo real').classes('text-h6')
                ui.label('📹 Lo que el agente esta viendo').classes('text-xs text-grey-7')

            screenshot_area = ui.column().classes(
                'w-full bg-grey-10 p-4 rounded-lg border'
            )
            with screenshot_area:
                ui.label('Los screenshots aparecran aqui...').classes('text-grey-7 text-center py-8')

        # ============================================================
        # Area de logs
        # ============================================================
        with ui.card().classes('w-full'):
            with ui.row().classes('items-center justify-between mb-2'):
                ui.label('Logs en tiempo real').classes('text-h6')
                ui.button(
                    icon='delete_sweep',
                    on_click=lambda: log_area.clear()
                ).props('flat dense').tooltip('Limpiar logs')

            log_area = ui.column().classes(
                'w-full h-96 overflow-y-auto bg-grey-10 p-4 rounded-lg border'
            ).style('font-family: monospace; font-size: 12px;')

        # ============================================================
        # Area de resultado
        # ============================================================
        result_card = ui.card().classes('w-full')
        with result_card:
            ui.label('El resultado aparecera aqui...').classes('text-grey-7 text-center py-8')

        # ============================================================
        # Handlers de eventos
        # ============================================================
        def on_detect_click():
            """Click en Detectar Calidades"""
            if not url_input.value:
                ui.notify('Por favor ingresa una URL', type='warning')
                return
            
            async def detect_task():
                detect_spinner.set_visibility(True)
                detect_btn.disable()
                
                try:
                    # Validar formato de URL
                    url = url_input.value.strip()
                    if not url.startswith("http://") and not url.startswith("https://"):
                        ui.notify('URL debe comenzar con http:// o https://', type='warning')
                        return
                    
                    detector = QualityDetector(headless=True)
                    qualities = detector.detect_qualities(url)
                    
                    if not qualities:
                        ui.notify('No se detectaron calidades en la página', type='warning')
                        return
                    
                    # Actualizar opciones de calidad
                    quality_options = {q["quality"]: f'{q["label"]}' for q in qualities}
                    quality_select.options = quality_options
                    quality_select.value = qualities[0]["quality"] if qualities else "1080p"
                    
                    ui.notify(f'Se detectaron {len(qualities)} calidades!', type='positive')
                    config_card.set_visibility(True)
                    
                except ValueError as e:
                    ui.notify(f'URL inválida: {str(e)[:50]}', type='warning')
                except Exception as e:
                    error_msg = str(e)[:100]
                    ui.notify(f'Error al detectar: {error_msg}', type='negative')
                finally:
                    detect_spinner.set_visibility(False)
                    detect_btn.enable()
            
            app.add_background_task(detect_task)

        def on_resolve_click():
            """Click en Resolver Link"""
            if not url_input.value:
                ui.notify('Por favor ingresa una URL', type='warning')
                return
            
            async def resolve_task():
                await resolve_link(
                    url=url_input.value,
                    quality=quality_select.value,
                    format_type=format_select.value,
                    providers=providers_select.value,
                    log_area=log_area,
                    result_card=result_card,
                    resolve_btn=resolve_btn,
                    spinner=resolve_spinner,
                    screenshot_area=screenshot_area,
                )
            
            app.add_background_task(resolve_task)

        # Asignar handlers
        detect_btn.on_click(on_detect_click)
        resolve_btn.on_click(on_resolve_click)

    # Footer
    with ui.footer().classes('bg-grey-9'):
        ui.label('Neo-Link-Resolver - Proyecto educacional').classes('text-grey-5 text-xs')


# =============================================================================
# Punto de entrada
# =============================================================================
if __name__ in {"__main__", "__mp_main__"}:
    import os
    
    # Crear directorio de screenshots si no existe
    screenshots_dir = os.path.join(os.path.dirname(__file__), '..', 'screenshots')
    os.makedirs(screenshots_dir, exist_ok=True)
    
    # Configurar NiceGUI
    try:
        app.add_static_files('/screenshots', screenshots_dir)
    except Exception as e:
        print(f"Warning: Could not add static files: {e}")
    
    # Construir UI
    build_ui()

    # Ejecutar servidor
    ui.run(
        title='Neo-Link-Resolver',
        port=8081,
        reload=False,
        show=True,
        favicon='🕶️',
    )

"""
gui.py - Interfaz grafica moderna para Neo-Link-Resolver.

Ejecutar:
    python src/gui.py

Abre un navegador con la interfaz en http://localhost:8080
"""

from nicegui import ui, app
import asyncio
from typing import Optional
from resolver import LinkResolver
from logger import get_logger
from matcher import LinkOption


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
):
    """
    Ejecuta la resolucion de forma asincrona y actualiza la UI.
    """
    state.is_resolving = True
    state.result = None
    resolve_btn.disable()
    spinner.set_visibility(True)

    # Limpiar area de logs
    log_area.clear()

    # Callback para recibir logs en tiempo real
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

        # Auto-scroll al final
        log_area.scroll_to(percent=1.0)

    # Registrar callback
    logger = get_logger()
    logger.clear()
    logger.register_callback(log_callback)

    # Ejecutar resolucion en thread separado (para no bloquear UI)
    def run_resolver():
        resolver = LinkResolver(headless=False)
        return resolver.resolve(url, quality, format_type, providers)

    # Ejecutar en executor (thread pool)
    result = await asyncio.get_event_loop().run_in_executor(
        None, run_resolver
    )

    # Actualizar resultado
    state.result = result
    state.is_resolving = False
    resolve_btn.enable()
    spinner.set_visibility(False)

    # Mostrar resultado
    result_card.clear()
    with result_card:
        if result and result.url != "LINK_NOT_RESOLVED":
            ui.label("Resolucion exitosa!").classes('text-h6 text-positive')
            ui.separator()
            
            # Link final (clickeable y copiable)
            ui.label("Link de descarga:").classes('text-bold mt-4')
            link_text = ui.input(
                value=result.url,
                readonly=True,
            ).classes('w-full font-mono').props('outlined dense')
            
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


# =============================================================================
# Construccion de la UI
# =============================================================================
def build_ui():
    """Construye la interfaz completa."""
    
    # Header
    with ui.header().classes('items-center justify-between bg-gradient-to-r from-indigo-500 to-purple-600'):
        with ui.row().classes('items-center gap-3'):
            ui.label('🕶️').classes('text-3xl')
            ui.label('Neo-Link-Resolver').classes('text-h5 text-white font-bold')
        ui.label('v0.4').classes('text-white text-sm')

    # Container principal
    with ui.column().classes('w-full max-w-6xl mx-auto p-6 gap-6'):
        
        # Descripcion
        with ui.card().classes('w-full'):
            ui.label('"There is no spoon... and there are no ads."').classes('text-italic text-grey-7')
            ui.label('Resuelve links de peliculas automaticamente, atravesando ads y acortadores.').classes('text-sm mt-2')

        # Formulario de entrada
        with ui.card().classes('w-full'):
            ui.label('Configuracion').classes('text-h6 mb-4')
            
            # URL input
            url_input = ui.input(
                label='URL de la pelicula',
                placeholder='https://hackstore.mx/peliculas/matrix-1999',
            ).classes('w-full').props('outlined clearable')

            # Grid de opciones
            with ui.grid(columns='1fr 1fr').classes('gap-4 mt-4 w-full'):
                # Calidad
                quality_select = ui.select(
                    label='Calidad',
                    options=['2160p', '1080p', '720p', '480p', '360p'],
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
                label='Proveedores preferidos (selecciona uno o mas)',
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

            # Boton de resolver
            with ui.row().classes('w-full justify-end gap-2 mt-6'):
                spinner = ui.spinner(size='sm', color='primary')
                spinner.set_visibility(False)
                
                resolve_btn = ui.button(
                    'Resolver Link',
                    icon='smart_toy',
                    on_click=lambda: asyncio.create_task(
                        resolve_link(
                            url=url_input.value,
                            quality=quality_select.value,
                            format_type=format_select.value,
                            providers=providers_select.value,
                            log_area=log_area,
                            result_card=result_card,
                            resolve_btn=resolve_btn,
                            spinner=spinner,
                        )
                    ) if url_input.value else ui.notify('Por favor ingresa una URL', type='warning')
                ).props('size=lg color=primary')

        # Area de logs (consola en tiempo real)
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

        # Area de resultado
        result_card = ui.card().classes('w-full')
        with result_card:
            ui.label('El resultado aparecera aqui...').classes('text-grey-7 text-center py-8')

    # Footer
    with ui.footer().classes('bg-grey-9'):
        ui.label('Neo-Link-Resolver - Proyecto educacional').classes('text-grey-5 text-xs')


# =============================================================================
# Punto de entrada
# =============================================================================
if __name__ in {"__main__", "__mp_main__"}:
    # Configurar NiceGUI
    app.add_static_files('/screenshots', 'screenshots')  # Para servir screenshots si es necesario
    
    # Construir UI
    build_ui()

    # Ejecutar servidor
    ui.run(
        title='Neo-Link-Resolver',
        port=8080,
        reload=False,
        show=True,  # Abre el navegador automaticamente
        favicon='🕶️',
    )

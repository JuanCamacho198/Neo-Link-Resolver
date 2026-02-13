"""
gui.py - Interfaz grafica moderna para Neo-Link-Resolver.

Ejecutar:
    python src/gui.py

Abre un navegador con la interfaz en http://localhost:8081
"""
import sys
import os
import asyncio

# FIX para Python 3.13 + Windows + NiceGUI
# Usamos WindowsProactorEventLoopPolicy que soporta subprocesos (necesario para Playwright)
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        print("Set event loop policy to ProactorEventLoopPolicy (required for Playwright)")
    except Exception as e:
        print(f"Warning: Could not set event loop policy: {e}")

# Agregar el directorio actual (src) al path para imports relativos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Importando dependencias...")
from nicegui import ui, app
import asyncio
from typing import Optional, List, Dict
print("Importando resolver...")
from resolver import LinkResolver
from logger import get_logger
from matcher import LinkOption
from quality_detector import QualityDetector
from history_manager import HistoryManager, ResolutionRecord
import multiprocessing
import queue
print("Dependencias cargadas.")


# =============================================================================
# Estado global de la aplicacion
# =============================================================================
class AppState:
    def __init__(self):
        self.resolver: Optional[LinkResolver] = None
        self.is_resolving: bool = False
        self.result: Optional[LinkOption] = None
        self.history_manager = HistoryManager()
        self.current_filter = "all"  # all, favorites
        
        # Network Interception Settings
        self.block_ads = True
        self.speed_up_timers = True
        self.network_stats = {"blocked": 0, "captured": 0}


state = AppState()


# =============================================================================
# Funciones auxiliares para historial y exportacion
# =============================================================================
def render_history_table(records: List[ResolutionRecord], history_area):
    """Renderiza la tabla de historial"""
    history_area.clear()
    
    if not records:
        with history_area:
            ui.label("No hay registros en el historial").classes('text-grey-7 text-center py-4')
        return
    
    with history_area:
        # Header
        with ui.row().classes('w-full gap-1 p-2 bg-grey-9 rounded font-bold text-sm sticky top-0'):
            ui.label('⭐').classes('w-8 text-center')
            ui.label('URL Original').classes('flex-grow truncate')
            ui.label('Proveedor').classes('w-24')
            ui.label('Calidad').classes('w-16')
            ui.label('Score').classes('w-12')
            ui.label('Acciones').classes('w-32')
        
        # Registros
        for record in records:
            with ui.row().classes('w-full gap-1 p-2 border-b hover:bg-grey-10 items-center text-xs'):
                # Favorito
                def make_toggle_fav(rec_id):
                    def toggle():
                        state.history_manager.toggle_favorite(rec_id)
                        refresh_history_display(history_area)
                    return toggle
                
                ui.button(
                    '⭐' if record.is_favorite else '☆',
                    on_click=make_toggle_fav(record.id)
                ).props('flat dense').classes('w-8')
                
                # URL (truncada)
                url_short = record.original_url[:40] + "..." if len(record.original_url) > 40 else record.original_url
                ui.label(url_short).classes('flex-grow truncate').tooltip(record.original_url)
                
                # Proveedor
                ui.label(record.provider or '-').classes('w-24')
                
                # Calidad
                ui.label(record.quality or '-').classes('w-16')
                
                # Score
                score_color = 'positive' if record.score >= 70 else 'warning' if record.score >= 40 else 'negative'
                ui.label(f'{record.score:.0f}').classes(f'w-12 text-{score_color}')
                
                # Acciones
                with ui.row().classes('w-32 gap-1'):
                    # Copiar link
                    def make_copy(url):
                        def copy():
                            ui.run_javascript(f'navigator.clipboard.writeText("{url}")')
                            ui.notify('Link copiado!', type='positive')
                        return copy
                    
                    ui.button(
                        icon='content_copy',
                        on_click=make_copy(record.resolved_url)
                    ).props('flat dense size=sm').tooltip('Copiar')
                    
                    # Eliminar
                    def make_delete(rec_id):
                        def delete():
                            state.history_manager.delete_record(rec_id)
                            refresh_history_display(history_area)
                            ui.notify('Registro eliminado', type='positive')
                        return delete
                    
                    ui.button(
                        icon='delete',
                        on_click=make_delete(record.id)
                    ).props('flat dense size=sm').tooltip('Eliminar')


def refresh_history_display(history_area):
    """Recarga la tabla de historial con el filtro actual"""
    if state.current_filter == "favorites":
        records = state.history_manager.get_favorites()
    else:
        records = state.history_manager.get_all_records()
    
    render_history_table(records, history_area)


# =============================================================================
# Funciones de resolucion (async wrapper)
# =============================================================================
async def resolve_link(
    url: str,
    quality: str,
    format_type: str,
    providers: list,
    log_area,
    logs_card,
    result_card,
    resolve_btn,
    resolve_progress_container,
    resolve_status,
    screenshot_area,
    screenshot_card,
):
    """
    Ejecuta la resolucion de forma asincrona y actualiza la UI.
    Incluye manejo robusto de errores.
    """
    state.result = None
    resolve_btn.disable()
    resolve_progress_container.set_visibility(True)
    logs_card.set_visibility(True)  # Mostrar logs
    screenshot_card.set_visibility(True)  # Mostrar screenshots

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

        # Actualizar estado también
        if level in ["STEP", "INIT"]:
            resolve_status.set_text(message[:100])

        # Agregar log a la UI
        with log_area:
            ui.label(message).classes(f'text-{color} text-xs font-mono')

    # Registrar callbacks
    logger = get_logger()
    logger.clear()
    logger.register_callback(log_callback)

    # Ejecutar resolucion en thread separado usando el resolver sin crono
    # Ahora funciona porque cambiamos a ProactorEventLoopPolicy que soporta subprocesos
    def run_resolver():
        try:
            logger.log("INFO", "Initializing resolver...")
            resolver = LinkResolver(headless=False, screenshot_callback=screenshot_callback)
            logger.log("INFO", "Resolver created successfully")
            
            # Aplicar configuraciones de interceptación
            resolver.use_network_interception = state.block_ads
            resolver.accelerate_timers = state.speed_up_timers
            logger.log("INFO", f"Settings: block_ads={state.block_ads}, speed_up_timers={state.speed_up_timers}")
            
            logger.log("INFO", "Starting resolution...")
            result = resolver.resolve(url, quality, format_type, providers, language)
            logger.log("INFO", f"Resolution completed. Result: {result}")
            
            return result
        except Exception as e:
            logger.log("ERROR", f"Resolver exception: {str(e)}")
            import traceback
            logger.log("ERROR", traceback.format_exc())
            return None

    # Ejecutar en executor (thread pool)
    # Con ProactorEventLoopPolicy, Playwright puede crear subprocesos correctamente
    try:
        logger.log("INFO", "Submitting resolver task to executor...")
        result = await asyncio.get_event_loop().run_in_executor(
            None, run_resolver
        )
        logger.log("INFO", "Resolver task completed")
    except Exception as e:
        logger.log("ERROR", f"Task execution failed: {str(e)}")
        import traceback
        logger.log("ERROR", traceback.format_exc())
        result = None

    # Actualizar resultado
    state.result = result
    resolve_btn.enable()
    resolve_progress_container.set_visibility(False)

    # Mostrar resultado
    result_card.clear()
    with result_card:
        try:
            if result and result.url != "LINK_NOT_RESOLVED":
                ui.label("✅ ¡Resolucion exitosa!").classes('text-h6 text-positive')
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
                ui.label("❌ No se pudo resolver el link").classes('text-h6 text-negative')
                ui.label("Revisa los logs para mas detalles.").classes('text-grey-7')
                if screenshot_list:
                    ui.label(f"Se capturaron {len(screenshot_list)} screenshots que puedes revisar en la seccion de visualizacion.").classes('text-xs text-warning mt-2')
        except Exception as e:
            ui.label("Error displaying results").classes('text-h6 text-negative')
            ui.label(f"Details: {str(e)[:100]}").classes('text-xs text-grey-7')


# =============================================================================
# Construccion de las tabs
# =============================================================================
def build_ui():
    """Construye la interfaz completa con selector de vista"""
    
    # Header
    with ui.header().classes('items-center justify-between bg-gradient-to-r from-indigo-500 to-purple-600'):
        with ui.row().classes('items-center gap-3'):
            ui.label('🕶️').classes('text-3xl')
            ui.label('Neo-Link-Resolver').classes('text-h5 text-white font-bold')
        ui.label('v0.5.0').classes('text-white text-sm')

    # Container principal
    with ui.column().classes('w-full max-w-6xl mx-auto p-6 gap-6'):
        
        # Descripcion
        with ui.card().classes('w-full'):
            ui.label('"There is no spoon... and there are no ads."').classes('text-italic text-grey-7')
            ui.label('Ingresa URL, detecta calidades, resuelve links automáticamente.').classes('text-sm mt-2')

        # Botones para cambiar entre vistas
        view_state = {'current': 'resolver'}
        view_container = ui.column().classes('w-full')
        
        with ui.row().classes('w-full gap-2 mb-4'):
            def show_resolver():
                view_state['current'] = 'resolver'
                refresh_view(view_container)
            
            def show_history():
                view_state['current'] = 'history'
                refresh_view(view_container)
            
            resolver_btn = ui.button('🔗 Resolver', on_click=show_resolver).props('outline')
            history_btn = ui.button('📚 Historial', on_click=show_history).props('outline')
        
        def refresh_view(container):
            container.clear()
            with container:
                if view_state['current'] == 'resolver':
                    build_resolver_tab()
                else:
                    build_history_tab()
        
        # Mostrar vista inicial
        with view_container:
            build_resolver_tab()

    # Footer
    with ui.footer().classes('bg-grey-9'):
        ui.label('Neo-Link-Resolver - Proyecto educacional').classes('text-grey-5 text-xs')


def build_resolver_tab():
    """Tab de resolucion de links"""
    
    with ui.column().classes('w-full gap-4'):
        # ============================================================
        # PASO 1: URL + Detectar Calidades
        # ============================================================
        with ui.card().classes('w-full'):
            ui.label('Paso 1: URL y Detectar').classes('text-h6 mb-4')
            
            with ui.column().classes('w-full gap-3'):
                # Row con URL input y boton
                with ui.row().classes('w-full gap-2'):
                    # URL input
                    url_input = ui.input(
                        label='URL',
                        placeholder='https://hackstore.mx/peliculas/matrix-1999',
                    ).classes('flex-grow').props('outlined clearable dense')
                    
                    detect_btn = ui.button(
                        'Detectar Calidades',
                        icon='auto_awesome',
                    ).props('outline color=primary')
                
                # Contenedor para el progreso (oculto al inicio)
                detect_progress_container = ui.column().classes('w-full')
                detect_progress_container.set_visibility(False)
                
                with detect_progress_container:
                    # Spinner grande y visible
                    with ui.row().classes('items-center gap-3 w-full'):
                        detect_spinner = ui.spinner(size='lg', color='primary')
                        ui.label('Detectando calidades...').classes('text-primary font-bold')
                    
                    # Barra de progreso indeterminada
                    detect_progress_bar = ui.linear_progress(value=0).props('indeterminate').classes('w-full')
                    
                    # Mensaje de estado
                    detect_status = ui.label('Navegando a la página...').classes('text-grey-7 text-sm mt-2')

        # ============================================================
        # PASO OPCIONAL: Network Interception Configuration
        # ============================================================
        with ui.card().classes('w-full border-l-4 border-blue'):
            with ui.row().classes('items-center justify-between w-full'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('bolt', color='blue', size='md')
                    ui.label('Network Interception (Auto-Evasión)').classes('text-h6')
                
                ui.badge('EXPERIMENTAL', color='blue')
            
            with ui.row().classes('w-full gap-8 mt-2'):
                ui.switch('Bloquear Anuncios', value=state.block_ads).bind_value(state, 'block_ads').tooltip('Bloquea dominios conocidos de publicidad')
                ui.switch('Acelerar Timers', value=state.speed_up_timers).bind_value(state, 'speed_up_timers').tooltip('Acelera los contadores de espera interrumpiendo setTimeout/setInterval')
            
            # Stats Panel (Visible cuando hay actividad)
            with ui.row().classes('w-full mt-4 p-2 bg-blue-50 rounded hidden') as stats_panel:
                ui.label('Ads Bloqueados:').classes('text-sm font-bold')
                ui.label('0').bind_text_from(state.network_stats, 'blocked').classes('text-sm')
                ui.label('|').classes('mx-2 text-blue-200')
                ui.label('Links Capturados:').classes('text-sm font-bold')
                ui.label('0').bind_text_from(state.network_stats, 'captured').classes('text-sm')

        # ============================================================
        # PASO 2: Seleccionar calidad y proveedores (oculto al inicio)
        # ============================================================
        config_card = ui.card().classes('w-full')
        config_card.set_visibility(False)
        
        with config_card:
            ui.label('Paso 2: Selecciona Opción y Proveedores').classes('text-h6 mb-4')
            
            # Calidad + Formato combinado
            quality_select = ui.select(
                label='Calidad / Formato',
                options=['1080p', '720p', '480p'],
                value='1080p',
            ).classes('w-full').props('outlined')

            # Proveedores dinámicos (se cargarán después del detection)
            providers_select = ui.select(
                label='Proveedores preferidos',
                options=['Cargando...'],
                value=['Cargando...'],
                multiple=True,
            ).classes('w-full mt-4').props('outlined')
            
            # Boton resolver y progreso
            with ui.row().classes('w-full justify-end gap-2 mt-6'):
                resolve_btn = ui.button(
                    'Resolver Link',
                    icon='smart_toy',
                ).props('size=lg color=positive')
            
            # Contenedor de progreso para resolver (oculto al inicio)
            resolve_progress_container = ui.column().classes('w-full')
            resolve_progress_container.set_visibility(False)
            
            with resolve_progress_container:
                # Barra de progreso y spinner
                with ui.row().classes('items-center gap-3 w-full mb-3'):
                    ui.spinner(size='lg', color='positive')
                    ui.label('Resolviendo link...').classes('text-positive font-bold')
                
                # Barra de progreso indeterminada
                ui.linear_progress(value=0).props('indeterminate').classes('w-full mb-2')
                
                # Mensaje de estado
                resolve_status = ui.label('Iniciando navegador...').classes('text-grey-7 text-sm')

        # ============================================================
        # Area de visualizacion (screenshots) - OCULTA AL INICIO
        # ============================================================
        screenshot_card = ui.card().classes('w-full')
        screenshot_card.set_visibility(False)
        
        with screenshot_card:
            with ui.row().classes('items-center justify-between mb-2'):
                ui.label('📹 Visualización en Tiempo Real').classes('text-h6')
                ui.button(
                    icon='close',
                    on_click=lambda: screenshot_card.set_visibility(False)
                ).props('flat dense').tooltip('Cerrar')
            
            screenshot_area = ui.column().classes(
                'w-full bg-grey-10 p-4 rounded-lg border'
            )
            with screenshot_area:
                ui.label('Los screenshots aparecerán aquí...').classes('text-grey-7 text-center py-8')

        # ============================================================
        # Area de logs - OCULTA AL INICIO
        # ============================================================
        logs_card = ui.card().classes('w-full')
        logs_card.set_visibility(False)
        
        with logs_card:
            with ui.row().classes('items-center justify-between mb-2'):
                ui.label('📋 Logs en Tiempo Real').classes('text-h6')
                ui.button(
                    icon='delete_sweep',
                    on_click=lambda: log_area.clear()
                ).props('flat dense').tooltip('Limpiar logs')
                ui.button(
                    icon='close',
                    on_click=lambda: logs_card.set_visibility(False)
                ).props('flat dense').tooltip('Cerrar')

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
        # Variables globales para almacenar estado
        # ============================================================
        detected_qualities = []  # Almacenar las calidades detectadas
        
        # ============================================================
        async def on_detect_click():
            """Click en Detectar Calidades"""
            if not url_input.value:
                ui.notify('Por favor ingresa una URL', type='warning')
                return
            
            detect_progress_container.set_visibility(True)
            detect_btn.disable()
            
            try:
                # Validar formato de URL
                url = url_input.value.strip()
                if not url.startswith("http://") and not url.startswith("https://"):
                    ui.notify('URL debe comenzar con http:// o https://', type='warning')
                    return
                
                detect_status.set_text('Navegando a la página...')
                detector = QualityDetector(headless=True)
                
                detect_status.set_text('Analizando estructura HTML...')
                qualities = detector.detect_qualities(url)
                
                if not qualities:
                    ui.notify('No se detectaron calidades en la página', type='warning')
                    return
                
                # Guardar las cualidades detectadas para usar en resolución
                detected_qualities.clear()
                detected_qualities.extend(qualities)
                
                detect_status.set_text(f'Se detectaron {len(qualities)} calidades')
                
                # Actualizar opciones de calidad con el display combinado
                quality_options = {q["display"]: q["display"] for q in qualities}
                quality_select.options = quality_options
                quality_select.value = qualities[0]["display"] if qualities else "1080p"
                
                # Detectar proveedores disponibles
                detect_status.set_text('Detectando proveedores...')
                try:
                    from adapters import get_adapter
                    from playwright.sync_api import sync_playwright
                    
                    adapter = get_adapter(url)
                    if adapter:
                        with sync_playwright() as p:
                            context = p.chromium.launch(headless=True).new_context()
                            adapter.set_context(context)
                            providers = adapter.detect_providers(url)
                            context.browser.close()
                        
                        if providers:
                            providers_select.options = providers
                            providers_select.value = providers[:2] if len(providers) >= 2 else providers
                            detect_status.set_text(f'Se detectaron {len(providers)} proveedores')
                        else:
                            # Si no se detectan, usar opciones por defecto
                            default_providers = ['MediaFire', 'MEGA', 'Google Drive', 'uTorrent']
                            providers_select.options = default_providers
                            providers_select.value = default_providers[:2]
                            detect_status.set_text('Usando proveedores por defecto')
                    else:
                        # Si no hay adaptador, usar opciones por defecto
                        default_providers = ['MediaFire', 'MEGA', 'Google Drive', 'uTorrent']
                        providers_select.options = default_providers
                        providers_select.value = default_providers[:2]
                except Exception as e:
                    ui.notify(f'Error detectando proveedores: {str(e)[:50]}', type='warning')
                    # Usar opciones por defecto si hay error
                    default_providers = ['MediaFire', 'MEGA', 'Google Drive', 'uTorrent']
                    providers_select.options = default_providers
                    providers_select.value = default_providers[:2]
                
                ui.notify(f'✅ Se detectaron {len(qualities)} calidades!', type='positive')
                config_card.set_visibility(True)
                
            except ValueError as e:
                ui.notify(f'URL inválida: {str(e)[:50]}', type='warning')
            except Exception as e:
                error_msg = str(e)[:100]
                ui.notify(f'Error al detectar: {error_msg}', type='negative')
            finally:
                detect_progress_container.set_visibility(False)
                detect_btn.enable()

        async def on_resolve_click():
            """Click en Resolver Link"""
            if not url_input.value:
                ui.notify('Por favor ingresa una URL', type='warning')
                return
            
            # Procesar la calidad seleccionada (está combinada con formato)
            selected_quality_display = quality_select.value
            quality_info = next(
                (q for q in detected_qualities if q["display"] == selected_quality_display),
                {"quality": "1080p", "format": ""}
            )
            
            await resolve_link(
                url=url_input.value,
                quality=quality_info.get("quality", "1080p"),
                format_type=quality_info.get("format", ""),
                providers=providers_select.value,
                log_area=log_area,
                logs_card=logs_card,
                result_card=result_card,
                resolve_btn=resolve_btn,
                resolve_progress_container=resolve_progress_container,
                resolve_status=resolve_status,
                screenshot_area=screenshot_area,
                screenshot_card=screenshot_card,
            )

        # Asignar handlers
        detect_btn.on_click(on_detect_click)
        resolve_btn.on_click(on_resolve_click)


def build_history_tab():
    """Tab de historial y favoritos"""
    
    with ui.column().classes('w-full gap-4'):
        # Encabezado con filtros y opciones
        with ui.card().classes('w-full'):
            ui.label('Historial de Links Resueltos').classes('text-h6 mb-4')
            
            # Fila de controles
            with ui.row().classes('w-full gap-2'):
                # Filtro
                def on_filter_change(filter_type: str):
                    state.current_filter = filter_type
                    refresh_history_display(history_area)
                
                with ui.row().classes('gap-1'):
                    ui.label('Filtro:').classes('text-bold')
                    all_btn = ui.button('Todos', on_click=lambda: on_filter_change("all")).props('outline size=sm')
                    fav_btn = ui.button('⭐ Favoritos', on_click=lambda: on_filter_change("favorites")).props('outline size=sm')
                
                ui.separator().classes('mx-2')
                
                # Exportar
                with ui.row().classes('gap-1'):
                    ui.label('Exportar:').classes('text-bold')
                    
                    def export_to_format(format_type: str):
                        records = state.history_manager.get_all_records()
                        if not records:
                            ui.notify('No hay registros para exportar', type='warning')
                            return
                        
                        if format_type == "json":
                            success, result = state.history_manager.export_to_json(records)
                        else:
                            success, result = state.history_manager.export_to_csv(records)
                        
                        if success:
                            ui.notify(f'✅ Exportado a {format_type.upper()}: {result}', type='positive')
                        else:
                            ui.notify(f'❌ Error exportando: {result}', type='negative')
                    
                    ui.button('JSON', on_click=lambda: export_to_format("json")).props('outline size=sm')
                    ui.button('CSV', on_click=lambda: export_to_format("csv")).props('outline size=sm')
                
                ui.separator().classes('mx-2')
                
                # Estadísticas
                def show_stats():
                    stats = state.history_manager.get_statistics()
                    message = f"""
                    📊 Estadísticas del Historial:
                    
                    Total de registros: {stats.get('total_records', 0)}
                    Favoritos: {stats.get('total_favorites', 0)}
                    Tasa de éxito: {stats.get('success_rate', 0):.1f}%
                    Proveedor más usado: {stats.get('most_used_provider', 'N/A')}
                    Calidad más usada: {stats.get('most_used_quality', 'N/A')}
                    Score promedio: {stats.get('average_score', 0):.1f}
                    """
                    ui.notify(message, type='info')
                
                ui.button('📊 Stats', on_click=show_stats).props('outline size=sm')
        
        # Area de historial
        history_card = ui.card().classes('w-full')
        with history_card:
            history_area = ui.column().classes('w-full gap-2 overflow-auto max-h-96')
            
            # Cargar historial inicial
            refresh_history_display(history_area)


# =============================================================================
# Punto de entrada
# =============================================================================
@ui.page('/')
def main_page():
    print("Nueva conexión recibida, construyendo UI...")
    try:
        # build_ui crea su propio ui.header y ui.footer, que NO pueden estar dentro
        # de un ui.column() genérico como intentamos antes.
        # Quitamos el ui.column() envolvente para evitar el RuntimeError.
        build_ui()
        print("UI construida exitosamente.")
    except Exception as e:
        print(f"Error construyendo UI: {e}")
        import traceback
        traceback.print_exc()
        ui.label(f"Error fatal al cargar la interfaz: {e}").classes('text-negative p-4')

if __name__ in {"__main__", "__mp_main__"}:
    import os
    
    print("Iniciando aplicación...")
    
    # Crear directorio de screenshots si no existe
    screenshots_dir = os.path.join(os.path.dirname(__file__), '..', 'screenshots')
    os.makedirs(screenshots_dir, exist_ok=True)
    
    # Configurar NiceGUI
    try:
        app.add_static_files('/screenshots', screenshots_dir)
        print(f"Archivos estáticos configurados en: {screenshots_dir}")
    except Exception as e:
        print(f"Warning: Could not add static files: {e}")
    
    PORT = 8088
    print(f"Lanzando servidor en http://127.0.0.1:{PORT} ...")
    
    # Ejecutar servidor con configuración estándar y segura
    ui.run(
        title='Neo-Link-Resolver',
        host='127.0.0.1', 
        port=PORT,
        reload=False,     # Importante para evitar bucles en Windows
        dark=True,
        show=False,       # Desactivamos auto-apertura para evitar condiciones de carrera
    )

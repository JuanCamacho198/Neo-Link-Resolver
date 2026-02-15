"""
gui_streamlit.py - Alternativa robusta de UI usando Streamlit.

Ejecutar:
    streamlit run src/gui_streamlit.py
"""
import streamlit as st
import sys
import os
import pandas as pd
import time
from typing import List

# Agregar src al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from resolver import LinkResolver
from history_manager import HistoryManager, ResolutionRecord
from quality_detector import QualityDetector
from logger import get_logger

# Configuración de página
st.set_page_config(
    page_title="Neo-Link-Resolver",
    page_icon="🕶️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #ff4b4b;
        color: white;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #ccc;
        margin-bottom: 1rem;
    }
    .success {
        background-color: #d4edda;
        color: #155724;
        border-color: #c3e6cb;
    }
    .error {
        background-color: #f8d7da;
        color: #721c24;
        border-color: #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Gestión del Estado
# =============================================================================
if "logs" not in st.session_state:
    st.session_state.logs = []

if "resolver_result" not in st.session_state:
    st.session_state.resolver_result = None

if "detected_qualities" not in st.session_state:
    st.session_state.detected_qualities = []

if "detected_providers" not in st.session_state:
    st.session_state.detected_providers = []

# =============================================================================
# Callbacks
# =============================================================================
def log_callback(level, message):
    """Callback para capturar logs en tiempo real"""
    formatted_msg = f"[{level}] {message}"
    st.session_state.logs.append(formatted_msg)
    # Streamlit no soporta actualizaciones parciales en medio de la ejecución fácilmente,
    # pero podemos usar contenedores vacíos. Ver abajo.

def screenshot_callback(filepath, name, description, url):
    """Callback para screenshots"""
    # Guardamos en session state para mostrar al final o durante si es posible
    if "screenshots" not in st.session_state:
        st.session_state.screenshots = []
    
    st.session_state.screenshots.append({
        "path": filepath,
        "name": name,
        "desc": description
    })

# =============================================================================
# Helper Functions
# =============================================================================
def get_history_df():
    hm = HistoryManager()
    records = hm.get_all_records()
    if not records:
        return pd.DataFrame()
    
    data = [r.to_dict() for r in records]
    df = pd.DataFrame(data)
    # Reordenar columnas
    cols = ['timestamp', 'original_url', 'quality', 'provider', 'score', 'is_favorite', 'resolved_url']
    existing_cols = [c for c in cols if c in df.columns]
    return df[existing_cols]

# =============================================================================
# Interfaz Principal
# =============================================================================
st.title("🕶️ Neo-Link-Resolver")
st.caption('"There is no spoon... and there are no ads."')

# Sidebar: Configuración y Historial
with st.sidebar:
    st.header("⚙️ Configuración")
    
    st.subheader("Network Interception")
    block_ads = st.toggle("Bloquear Anuncios", value=True, help="Bloquea dominios de publicidad conocidos")
    speed_up_timers = st.toggle("Acelerar Timers", value=True, help="Intenta saltar cuentas regresivas")
    
    st.divider()
    
    st.subheader("📚 Historial Reciente")
    hm_sidebar = HistoryManager()
    favs = hm_sidebar.get_favorites()
    if favs:
        st.write("⭐ Favoritos:")
        for f in favs[:5]:
            if st.button(f"{f.provider} - {f.quality}", key=f"fav_{f.id}"):
                st.code(f.resolved_url)
    else:
        st.info("No hay favoritos guardados.")

# Tabs principales
tab_resolver, tab_history = st.tabs(["🔗 Resolver Links", "📜 Historial Completo"])

with tab_resolver:
    # Paso 1: Input URL
    col1, col2 = st.columns([3, 1])
    with col1:
        url_input = st.text_input("URL de la película", placeholder="https://hackstore.mx/...", key="url_input")
    with col2:
        st.write("") # Spacer
        st.write("") # Spacer
        detect_btn = st.button("🔍 Detectar Opciones")

    # Contenedor para resultados de detección
    options_container = st.container()

    if detect_btn and url_input:
        with st.spinner("Analizando sitio..."):
            try:
                # 1. Detectar Calidades
                detector = QualityDetector(headless=True)
                qs = detector.detect_qualities(url_input)
                st.session_state.detected_qualities = qs
                
                # 2. Detectar Proveedores (Simulado por ahora o real si adapter existe)
                # Por simplicidad usamos defaults si falla, similar a gui.py
                try:
                    from adapters import get_adapter
                    from playwright.sync_api import sync_playwright
                    adapter = get_adapter(url_input)
                    if adapter:
                        with sync_playwright() as p:
                            browser = p.chromium.launch(headless=True)
                            context = browser.new_context()
                            adapter.set_context(context)
                            providers = adapter.detect_providers(url_input)
                            browser.close()
                            st.session_state.detected_providers = providers
                    else:
                        st.session_state.detected_providers = ['MediaFire', 'MEGA', 'Google Drive', 'uTorrent']
                except:
                    st.session_state.detected_providers = ['MediaFire', 'MEGA', 'Google Drive', 'uTorrent']

                if not qs:
                    st.warning("No se detectaron calidades específicas. Se usarán valores por defecto.")
                    st.session_state.detected_qualities = [{"display": "1080p WEB-DL", "quality": "1080p", "format": "WEB-DL"}]
                
                st.success(f"Detectado: {len(st.session_state.detected_qualities)} opciones y {len(st.session_state.detected_providers)} proveedores.")
            
            except Exception as e:
                st.error(f"Error al analizar: {e}")

    # Paso 2: Selección y Resolución
    if st.session_state.detected_qualities:
        with st.form("resolve_form"):
            st.subheader("Selecciona tus preferencias")
            c1, c2 = st.columns(2)
            
            with c1:
                display_opts = [q["display"] for q in st.session_state.detected_qualities]
                selected_display = st.selectbox("Calidad / Formato", display_opts)
            
            with c2:
                providers_opts = st.session_state.detected_providers if st.session_state.detected_providers else ['MediaFire', 'MEGA', 'Google Drive']
                selected_providers = st.multiselect("Proveedores", providers_opts, default=providers_opts[:2])
            
            submitted = st.form_submit_button("🚀 Iniciar Resolución")
            
            if submitted:
                # Preparar consola de logs
                log_container = st.empty()
                st.session_state.logs = [] # Limpiar logs anteriores
                st.session_state.screenshots = [] # Limpiar screenshots
                
                # Configurar Logger para escribir en Streamlit
                logger = get_logger()
                logger.clear()
                
                # Custom handler que actualiza un placeholder de streamlit
                # NOTA: Streamlit no es async-friendly para updates en tiempo real desde threads background facilmente.
                # Lo haremos sincrono y actualizaremos logs en bloque o usando st.status
                
                status_text = "Iniciando..."
                with st.status("Resolviendo enlace...", expanded=True) as status:
                    
                    # Wrapper del callback para escribir en el status y guardar
                    def st_log_callback(level, msg):
                        st.write(f"`[{level}]` {msg}")
                        st.session_state.logs.append(f"[{level}] {msg}")
                    
                    logger.register_callback(st_log_callback)
                    
                    # Encontrar datos seleccionados
                    selected_q_data = next(q for q in st.session_state.detected_qualities if q["display"] == selected_display)
                    
                    # Instanciar Resolver
                    resolver = LinkResolver(
                        headless=False, # Verlo ayuda a debuggear, o headless=True
                        screenshot_callback=screenshot_callback
                    )
                    resolver.use_network_interception = block_ads
                    resolver.accelerate_timers = speed_up_timers
                    
                    # Ejecutar (bloqueante)
                    result = resolver.resolve(
                        url=url_input,
                        quality=selected_q_data.get("quality", "1080p"),
                        format_type=selected_q_data.get("format", "WEB-DL"),
                        providers=selected_providers
                    )
                    
                    st.session_state.resolver_result = result
                    
                    if result and result.url != "LINK_NOT_RESOLVED":
                        status.update(label="¡Completado!", state="complete", expanded=False)
                    else:
                        status.update(label="Falló la resolución", state="error", expanded=True)

        # Mostrar Resultado
        if st.session_state.resolver_result:
            result = st.session_state.resolver_result
            st.divider()
            
            if result.url and result.url != "LINK_NOT_RESOLVED":
                st.balloons()
                st.markdown(f"""
                <div class="status-box success">
                    <h3>✅ Link Resuelto Exitosamente</h3>
                    <p><strong>Proveedor:</strong> {result.provider}</p>
                    <p><strong>Calidad:</strong> {result.quality}</p>
                    <p><strong>Score:</strong> {result.score}/100</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.text_input("Link Final (Copia y pega)", value=result.url)
                st.markdown(f"[Abrir Link]({result.url})")
            else:
                st.error("❌ No se pudo resolver el link. Revisa los logs.")

        # Galería de Screenshots
        if "screenshots" in st.session_state and st.session_state.screenshots:
            st.subheader("📸 Capturas del proceso")
            cols = st.columns(3)
            for i, shot in enumerate(st.session_state.screenshots):
                with cols[i % 3]:
                    st.image(shot["path"], caption=f"{shot['name']} - {shot['desc']}")

with tab_history:
    st.header("Historial de Resoluciones")
    df = get_history_df()
    
    if not df.empty:
        st.dataframe(
            df,
            column_config={
                "resolved_url": st.column_config.LinkColumn("Resolved Link"),
                "is_favorite": st.column_config.CheckboxColumn("Favorito"),
                "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%f"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Botones de exportación
        c1, c2 = st.columns(2)
        with c1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Descargar CSV",
                csv,
                "history.csv",
                "text/csv",
                key='download-csv'
            )
        with c2:
            json_str = df.to_json(orient="records")
            st.download_button(
                "📥 Descargar JSON",
                json_str,
                "history.json",
                "application/json",
                key='download-json'
            )
    else:
        st.info("El historial está vacío.")


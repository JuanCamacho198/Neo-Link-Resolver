"""
vision_config.py - Configuración para Fase 2 (Visión Computacional)

Define parámetros, prompts, y configuraciones para el analizador de visión.
"""

from enum import Enum
from typing import List


class ButtonType(Enum):
    """Tipos de botones que se pueden detectar"""
    REAL = "real"
    FAKE = "fake"
    UNKNOWN = "unknown"
    AD = "ad"
    NAV = "navigation"


# =============================================================================
# Configuración de Prompts para Vision
# =============================================================================

VISION_ANALYSIS_PROMPT = """Analiza esta captura de pantalla de una página de descarga de películas.

TAREA CRÍTICA: Identifica TODOS los botones y elementos clickeables visibles.

Para CADA botón/elemento, proporciona:
1. Texto visible exacto (si lo hay)
2. Posición aproximada (arriba/abajo/izquierda/derecha/centro)
3. Tipo probable: real | fake | ad | navigation | unknown
4. Confianza (0-100%) de si es REAL vs FALSO
5. Razón detallada de tu clasificación
6. Contexto visual (¿aislado? ¿rodeado de publicidad? ¿animado?)

CRITERIOS PARA CLASIFICAR:

Botones REALES:
✅ Texto descriptivo y coherente ("Ver enlace", "Descargar", "Get Link")
✅ Colores sutiles (azul, gris, blanco, verde oscuro)
✅ Tamaño medio y proporcional
✅ Fuente clara y legible
✅ Aislado o en contexto legítimo
✅ No tiene atributos sospechosos
✅ Ubicación lógica en la página

Botones FALSOS:
❌ Texto exagerado ("CLICK AQUÍ!!!", "GANAR PREMIO", "FREE DOWNLOAD")
❌ Colores fluorescentes/llamativos (rojo brillante, naranja, amarillo)
❌ Tamaño anormalmente grande
❌ Múltiples botones idénticos muy cerca
❌ Rodeado de publicidad
❌ Animaciones o parpadeos
❌ Ubicación sospechosa (esquinas, flotante)
❌ Texto en mayúsculas con signos de exclamación

ANÁLISIS DE PÁGINA:
- ¿Cuántos botones totales hay?
- ¿Qué densidad de publicidad observas?
- ¿Hay claras señales de sitio legítimo o spam?
- ¿Cuáles son las señales de alerta?

Responde COMO JSON (válido y parseble):
{
    "buttons_found": [
        {
            "text": "texto del botón",
            "position": "arriba-derecha | arriba-centro | centro | etc",
            "type": "real|fake|ad|navigation|unknown",
            "confidence": 85,
            "reason": "explicación detallada",
            "color": "color observado",
            "size": "small|medium|large",
            "isolated": true|false,
            "coordinates_hint": "si puedes estimar aprox"
        }
    ],
    "page_analysis": {
        "total_buttons": 7,
        "has_multiple_buttons": true,
        "ad_density": "high|medium|low",
        "estimated_real_button_count": 1,
        "warning_signs": ["lista", "de", "señales"],
        "page_legitimacy": "high|medium|low"
    },
    "recommendations": [
        "Click en 'Ver Enlace' - es el botón real con 95% confianza",
        "Evitar botones rojo con texto en mayúsculas",
        "Cerrar popups que aparezcan"
    ],
    "confidence_score": 85
}

IMPORTANTE:
- Sé riguroso en tu análisis
- Explica el PORQUÉ de cada clasificación
- Si algo parece sospechoso, indica por qué
- La respuesta DEBE ser JSON válido
"""

# Prompt simplificado para análisis rápido
VISION_QUICK_PROMPT = """Analiza esta página de descarga. ¿Cuál es el botón de descarga REAL?

Describe: texto, color, posición.
Confianza: 0-100%
Razón: 1-2 líneas.

Formato: JSON con campos: text, position, confidence, reason
"""


# =============================================================================
# Configuración de Umbrales
# =============================================================================

class ConfidenceThresholds:
    """Umbrales de confianza para diferentes acciones"""
    
    # Mínimo para clickear sin confirmación
    AUTO_CLICK_MIN = 0.80  # 80%
    
    # Mínimo para mostrar en recomendaciones
    SHOW_RECOMMENDATION_MIN = 0.60  # 60%
    
    # Mínimo para considerar resultado válido
    VALID_ANALYSIS_MIN = 0.40  # 40%
    
    # Mínimo para alertar al usuario
    ALERT_THRESHOLD = 0.70  # 70% seguros de que algo es falso


# =============================================================================
# Patrones de Texto para Detectar Botones Reales
# =============================================================================

REAL_BUTTON_KEYWORDS = [
    "ver enlace",
    "ver link",
    "get link",
    "download",
    "descargar",
    "ver descargar",
    "click para ver",
    "obtener enlace",
    "acceso directo",
    "ir al enlace",
    "botón de descarga",
    "desbloquear",
    "ver contenido",
]

FAKE_BUTTON_KEYWORDS = [
    "click aquí",
    "click here",
    "ganar",
    "premio",
    "gratis",
    "free",
    "winner",
    "wow",
    "sorpresa",
    "regalo",
    "descargar ahora",
    "apúrate",
    "limitado",
    "oferta",
]

# Palabras que aparecen frecuentemente en botones de publicidad
ADVERTISEMENT_KEYWORDS = [
    "casino",
    "poker",
    "apuesta",
    "bet",
    "juego",
    "game",
    "dinero",
    "money",
    "ganar dinero",
    "earn",
    "cupón",
    "coupon",
]


# =============================================================================
# Configuración de Colores
# =============================================================================

class ColorAnalysis:
    """Análisis de colores para detectar botones"""
    
    LEGITIMATE_COLORS = [
        'blue', 'dark blue', 'light blue',
        'gray', 'grey', 'dark gray',
        'white', 'black',
        'dark green', 'green',
        'purple', 'dark purple',
    ]
    
    SUSPICIOUS_COLORS = [
        'red', 'bright red', 'crimson',
        'orange', 'orange red',
        'neon', 'fluorescent',
        'yellow', 'bright yellow',
        'pink', 'hot pink',
    ]


# =============================================================================
# Configuración de Modelos
# =============================================================================

class ModelConfig:
    """Configuración de modelos de vision"""
    
    # OpenAI GPT-4o Vision
    OPENAI_MODEL = "gpt-4-vision-preview"
    OPENAI_MAX_TOKENS = 1024
    
    # LLaVA Local
    LLAVA_MODEL = "llava:13b"  # o "llava:7b" para menor VRAM
    LLAVA_TEMPERATURE = 0.1  # Bajo para análisis más determinístico
    
    # Timeouts
    ANALYSIS_TIMEOUT = 30  # segundos


# =============================================================================
# Configuración de Almacenamiento
# =============================================================================

SCREENSHOTS_DIR = "data"
ANALYSIS_CACHE_DIR = "data/vision_cache"
ANALYSIS_HISTORY_FILE = "data/vision_analysis_history.json"


# =============================================================================
# Métricas y Logging
# =============================================================================

class MetricsConfig:
    """Configuración de métricas y tracking"""
    
    # Trackear cada análisis
    TRACK_ANALYSIS = True
    
    # Guardar screenshots para revisión
    SAVE_SCREENSHOTS = True
    
    # Guardar análisis en caché
    USE_CACHE = True
    CACHE_TTL = 3600  # 1 hora
    
    # Métricas que trackear
    METRICS = [
        "total_analyses",
        "successful_clicks",
        "failed_clicks",
        "average_confidence",
        "button_types_detected",
        "accuracy_per_site",
    ]


# =============================================================================
# Configuración por Sitio
# =============================================================================

SITE_CONFIGS = {
    "hackstore.mx": {
        "expected_button_text": "Ver enlace",
        "button_color": "blue",
        "button_position": "center",
        "typical_real_buttons": 1,
        "typical_fake_buttons": 4,
    },
    "peliculasgd.net": {
        "expected_button_text": "Ver enlace",
        "button_color": "blue",
        "button_position": "center",
        "typical_real_buttons": 1,
        "typical_fake_buttons": 3,
    },
}


# =============================================================================
# Funciones de Configuración
# =============================================================================

def get_site_config(domain: str) -> dict:
    """Obtiene configuración específica del sitio"""
    return SITE_CONFIGS.get(domain, SITE_CONFIGS.get("hackstore.mx"))


def get_confidence_threshold(action: str) -> float:
    """Obtiene umbral de confianza para una acción"""
    thresholds = {
        "auto_click": ConfidenceThresholds.AUTO_CLICK_MIN,
        "recommend": ConfidenceThresholds.SHOW_RECOMMENDATION_MIN,
        "valid": ConfidenceThresholds.VALID_ANALYSIS_MIN,
        "alert": ConfidenceThresholds.ALERT_THRESHOLD,
    }
    return thresholds.get(action, 0.5)

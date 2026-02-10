# Fase 2: Visión Computacional - "I Know Kung Fu"

## 🤖 Objetivo

Usar APIs de Vision (GPT-4o o LLaVA local) para analizar capturas de pantalla y **identificar automáticamente botones reales vs falsos** en páginas de descarga.

## 📊 Hito Principal

**Identificar correctamente el botón "Ver Enlace" entre 5 botones falsos** con al menos 80% de confianza.

---

## 🏗️ Arquitectura

```
Neo-Link-Resolver v0.5.0+
├── src/
│   ├── resolver.py (existente)
│   ├── vision_analyzer.py (NEW - Fase 2)
│   │   └── VisionAnalyzer class
│   │       ├── GPT-4o Vision support
│   │       └── LLaVA local support (future)
│   │
│   └── vision_resolver.py (NEW - Fase 2)
│       └── VisionResolver class
│           ├── analyze_page()
│           ├── find_and_click_button()
│           └── identify_download_button()
│
└── Pipeline:
    Screenshot → Vision Analysis → Button Detection → Click → Verify
```

---

## 🚀 Flujo de Navegación con Visión

### Paso 1: Captura de Pantalla
```python
screenshot_path = await page.screenshot('page.png')
```

### Paso 2: Análisis con Vision
```python
analyzer = VisionAnalyzer(provider='openai_gpt4v')
result = await analyzer.analyze_screenshot('page.png')
# Retorna: 
# - Botones detectados con posición, tipo, confianza
# - Análisis de publicidad/señales de alerta
# - Recomendaciones de acción
```

### Paso 3: Identificación de Botón Real
```python
real_buttons = analyzer.get_real_buttons(result)
best_button = analyzer.get_best_button(result)
# El más probable de ser real
```

### Paso 4: Click Automático
```python
vision_resolver = VisionResolver()
click_result = await vision_resolver.find_and_click_button(page)
# Busca el botón en el DOM y lo clickea
```

---

## 📋 Modelos Soportados

### 1️⃣ GPT-4o Vision (OpenAI) - RECOMENDADO
**Ventajas:**
- ✅ Muy preciso (~95% en identificación de botones)
- ✅ Entiende contexto visual complejo
- ✅ Detecta publicidad y señales de alerta
- ✅ Rápido (~3-5 segundos por análisis)

**Desventajas:**
- ❌ Requiere API key (costo ~$0.01 por análisis)
- ❌ Requiere conexión a internet

**Setup:**
```bash
# 1. Obtener API key en https://platform.openai.com
# 2. Guardar en .env
echo "OPENAI_API_KEY=sk-..." >> .env

# 3. Usar en código
from src.vision_analyzer import VisionAnalyzer
analyzer = VisionAnalyzer(provider='openai_gpt4v')
```

### 2️⃣ LLaVA Local (Ollama) - FUTURO
**Ventajas:**
- ✅ Totalmente local (sin costos)
- ✅ Sin límites de uso
- ✅ Privacidad total

**Desventajas:**
- ❌ Menos preciso (~80-85%)
- ❌ Más lento (~30-60 segundos)
- ❌ Requiere recursos de GPU

**Status:** Pendiente implementación

---

## 💻 Uso Básico

### Análisis Simple
```python
import asyncio
from src.vision_analyzer import VisionAnalyzer

async def main():
    analyzer = VisionAnalyzer(provider='openai_gpt4v')
    result = await analyzer.analyze_screenshot('screenshot.png')
    
    print(f"Confianza: {result.confidence:.1%}")
    print(f"Botones detectados: {len(result.detected_elements)}")
    
    for btn in result.detected_elements:
        print(f"  - {btn['text']}: {btn['type']} ({btn['confidence']}%)")

asyncio.run(main())
```

### Navegación con Visión
```python
from src.vision_resolver import VisionResolver
from playwright.async_api import async_playwright

async def navigate_with_vision():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        resolver = VisionResolver()
        
        # Navegar a página de descarga
        await page.goto('https://hackstore.mx/peliculas/matrix-1999')
        
        # Analizar página
        analysis = await resolver.analyze_page(page)
        print(f"Análisis: {analysis.confidence:.1%} confianza")
        
        # Encontrar y clickear botón real
        click = await resolver.find_and_click_button(page)
        print(f"Click: {click.button_text} - {'✅' if click.success else '❌'}")
        
        await browser.close()

asyncio.run(navigate_with_vision())
```

---

## 📊 Resultado del Análisis

Cada análisis retorna `AnalysisResult` con:

```python
{
    "provider": "openai_gpt4v",
    "image_path": "data/page.png",
    "detected_elements": [
        {
            "text": "Ver Enlace",
            "position": "arriba-derecha",
            "type": "real",
            "confidence": 95,
            "reason": "Botón azul, prominente, no está rodeado de publicidad",
            "coordinates_hint": "x: 500-600, y: 100-150"
        },
        {
            "text": "DESCARGA AHORA!",
            "position": "izquierda",
            "type": "fake",
            "confidence": 98,
            "reason": "Botón rojo brillante, texto en mayúsculas, rodeado de publicidad",
            "coordinates_hint": "x: 0-100, y: 200-250"
        }
    ],
    "button_analysis": {
        "has_multiple_buttons": true,
        "ad_density": "high",
        "estimated_real_button_count": 1,
        "warning_signs": [
            "Múltiples botones llamativos",
            "Alta densidad de publicidad",
            "Uso de texto en mayúsculas"
        ]
    },
    "recommendations": [
        "Click en botón 'Ver Enlace' (confianza 95%)",
        "Evitar botones rojo con mayúsculas",
        "Cerrar ventanas popup que se abran"
    ],
    "confidence": 0.95,
    "raw_response": "..."
}
```

---

## 🎯 Estrategia de Identificación

El analizador usa estos criterios para clasificar botones:

### Señales de Botón REAL:
✅ Texto descriptivo y coherente ("Ver enlace", "Descargar")  
✅ Colores sutiles (azul, gris, blanco)  
✅ Tamaño medio (no demasiado grande/pequeño)  
✅ Aislado o en contexto legítimo  
✅ No tiene atributos sospechosos  

### Señales de Botón FALSO:
❌ Texto exagerado ("CLICK AQUÍ!!!", "GANAR PREMIO")  
❌ Colores llamativos (rojo, naranja fluorescente)  
❌ Tamaño anormalmente grande  
❌ Rodeado de publicidad  
❌ Múltiples botones similares muy cerca  
❌ Animaciones o parpadeos  

---

## 🔧 Integración con Resolver Existente

Para usar visión en el resolver actual:

```python
from src.vision_resolver import enhance_resolver_with_vision

# En el adaptador de hackstore, por ejemplo:
async def click_with_vision(page, url):
    result = await enhance_resolver_with_vision(resolver, page, url)
    
    if result['click_result']['success']:
        print(f"✅ Botón clickeado: {result['click_result']['button']}")
    else:
        print(f"❌ Fallo: {result['click_result']['reason']}")
    
    return result
```

---

## 📈 Próximos Pasos

### Phase 2a: Implementación Base (Esta semana)
- [x] Crear módulo `vision_analyzer.py`
- [x] Crear módulo `vision_resolver.py`
- [ ] Integrar con GUI para mostrar análisis
- [ ] Crear tests con screenshots reales
- [ ] Medir accuracy en diferentes sitios

### Phase 2b: Optimización
- [ ] Fine-tuning del prompt de visión
- [ ] Caché de resultados
- [ ] Retry logic mejorado
- [ ] Soporte para LLaVA local
- [ ] Métricas de performance

### Phase 2c: Integración
- [ ] Integrar en adaptadores (hackstore, peliculasgd)
- [ ] Agregar opción en GUI para "usar visión"
- [ ] Tracking de éxito/fracaso
- [ ] Auto-learning del modelo

---

## 🧪 Testing

### Test 1: Análisis Simple
```bash
python src/vision_analyzer.py data/test_screenshot.png
```

### Test 2: Navegación con Visión
```bash
python tests/test_vision_resolver.py
```

### Test 3: Integración
```python
# En GUI, agregar botón "Resolver con Visión"
# Que ejecute:
result = await vision_resolver.find_and_click_button(page)
```

---

## 💰 Costos Estimados

### OpenAI GPT-4o Vision
- **Por análisis:** ~$0.01 USD
- **Por película:** ~$0.03 (3 análisis: entrada + búsqueda + descarga)
- **1000 películas:** ~$30 USD

### LLaVA Local
- **Por análisis:** $0 (costo de computación local)
- **Infraestructura:** GPU recomendada

---

## 📚 Referencias

- [OpenAI Vision API](https://platform.openai.com/docs/guides/vision)
- [GPT-4o Documentation](https://platform.openai.com/docs/models/gpt-4o)
- [LLaVA Project](https://github.com/haotian-liu/LLaVA)
- [Ollama Installation](https://ollama.ai)

---

## 🎯 Hito de Éxito

✅ **Identificar correctamente botones en 80%+ de páginas**
✅ **Tiempo de análisis < 5 segundos por página**
✅ **Funcionar en adaptadores (hackstore, peliculasgd)**
✅ **Integración con GUI existente**

**Status:** En desarrollo 🚀

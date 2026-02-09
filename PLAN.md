# 🕶️ Neo-Link-Resolver (Project Ad-ios)

> "There is no spoon... and there are no ads."

Un agente de navegación autónomo diseñado para evadir patrones oscuros, publicidad agresiva y acortadores de enlaces hostiles, utilizando Visión Computacional e IA Generativa.

## 🎯 Objetivo del Proyecto
Crear un agente capaz de navegar desde un enlace "sucio" (lleno de ads/shorteners) hasta el destino final (enlace de descarga/streaming) en sitios como `peliculasgd.net`, simulando comportamiento humano para evitar detección.

## 🛠️ Stack Tecnológico
- **Core:** Python 3.10+
- **Browser Automation:** Playwright (Stealth Mode)
- **Vision:** OpenAI GPT-4o / LLaVA (Local fallback)
- **Orchestration:** LangGraph (State Machine)
- **API:** FastAPI
- **Containerization:** Docker

## 🗺️ Roadmap (2 Meses)

### Mes 1: The "Wake Up" Phase (Fundamentos) ✅
- [x] Configurar entorno (Python, Playwright, dotenv).
- [x] Implementar **Playwright** básico para abrir `peliculasgd.net` (`src/main.py`).
- [x] Crear lógica de navegación basada en selectores CSS simples.
- [x] Mapear y documentar flujo completo de navegación (7 pasos, multiples pestañas).
- [x] Implementar simulación de comportamiento humano (`src/human_sim.py`).
- [x] Implementar pipeline completo: película -> enlaces publicos -> intermediarios -> Google -> verificación -> link final.
- [x] **NUEVO:** Arquitectura modular con sistema de adaptadores (multi-sitio).
- [x] **NUEVO:** Motor de matching inteligente por calidad/formato/proveedor (`src/matcher.py`).
- [x] **NUEVO:** Soporte para `hackstore.mx` con busqueda inteligente de links.
- [x] **NUEVO:** CLI con criterios de busqueda (`--quality`, `--format`, `--provider`).
- [x] **Hito:** Resolver links en 2 sitios diferentes con criterios personalizables.

### Mes 2: "I Know Kung Fu" (Visión Computacional) 🟡
- [ ] Integrar modelo de Visión (GPT-4o Vision o Local).
- [ ] Implementar sistema de "Screenshot -> Analysis -> Action".
- [ ] Entrenar/Promptear al modelo para distinguir botones reales de falsos ("Fake Download Buttons").
- [ ] **Hito:** El agente identifica correctamente el botón "Ver Enlace" entre 5 botones falsos.

### Mes 3: Dodging Bullets (Evasión y Resiliencia) 🟠
- [ ] Manejo de Pop-ups y nuevas pestañas (cerrarlas automáticamente).
- [ ] Espera inteligente de contadores (timers de 5-10s).
- [ ] Implementar `playwright-stealth` para evitar ser baneado.
- [ ] **Hito:** Navegación completa exitosa en el 80% de los intentos en `peliculasgd.net`.

### Mes 4: The Operator (API & Architecture) 🔵
- [ ] Envolver el agente en una API REST con FastAPI.
- [ ] Endpoint: `POST /resolve { "url": "..." }` -> Retorna link final.
- [ ] Cola de tareas (Redis/Celery) para manejar múltiples peticiones.

### Mes 5: "Guns. Lots of Guns." (Scaling & Docker) 🟣
- [ ] Dockerizar la solución (manejar Headless Browser en contenedor es un reto técnico interesante).
- [ ] Despliegue de prueba en una nube gratuita (Railway/Render) o servidor casero.

### Mes 6: The Architect (Demo & Polishing) ⚪
- [ ] Crear documentación técnica detallada (Architecture Diagrams).
- [ ] Grabar video demo mostrando la "visión" del agente en tiempo real.
- [ ] Escribir artículo de blog: "Cómo usé IA para arreglar la web rota".

## 🏗️ Arquitectura v0.3

```
src/
├── main.py              # CLI entry point con argumentos inteligentes
├── config.py            # SearchCriteria, constantes globales
├── matcher.py           # LinkMatcher: ranking de links por score
├── human_sim.py         # Simulacion de comportamiento humano
└── adapters/            # Sistema de adaptadores por sitio
    ├── base.py          # SiteAdapter (clase base abstracta)
    ├── peliculasgd.py   # PeliculasGDAdapter (7 pasos)
    └── hackstore.py     # HackstoreAdapter (extraccion directa)
```

### Flujo de resolucion inteligente:

1. **Usuario ejecuta**: `python main.py <url> --quality 1080p --format WEB-DL --provider utorrent`
2. **main.py** crea `SearchCriteria` con los parametros
3. **Adaptador** se selecciona automaticamente segun la URL
4. **Adaptador** navega y extrae todos los links disponibles
5. **LinkMatcher** rankea los links segun criterios (score 0-100)
6. **Resultado**: Se retorna el link con mayor score

### SearchCriteria (sistema de scoring):
- **Quality match (40 pts)**: Link exacto con calidad deseada
- **Format match (30 pts)**: Link exacto con formato deseado  
- **Provider preference (30 pts)**: Proveedor esta en lista de preferidos
- **Language bonus (+10 pts)**: Link contiene idioma deseado

## 🗂️ Flujo de Navegacion (peliculasgd.net -> Link Final)

El agente debe resolver la siguiente cadena de redirecciones y anti-bots:

```
Pagina de pelicula (peliculasgd.net)
  |
  v  Click en imagen "Enlaces Publicos" (img.wp-image-125438)
  |
Pagina intermedia 1 (ej: neworldtravel.com)  [nueva pestana]
  |
  v  Click en div.text "Haz clic aqui"
  |
Pagina intermedia 2 (ej: saboresmexico.com)  [nueva pestana]
  |
  v  Click en button.button-s "CLIC AQUI PARA CONTINUAR"
  |
Busqueda de Google  [nueva pestana]
  |
  v  Click en primer resultado de busqueda
  |
Pagina de verificacion humana
  |  - Mover mouse, hacer scroll, clicks aleatorios
  v  Click en boton "Continuar" (button.button-s con initSystem())
  |
Pagina de anuncio obligatorio
  |  - Click en anuncio (#click_message)
  |  - Esperar ~40 segundos
  v
  |
Volver a Pagina intermedia 1 -> Link final disponible
```

### Selectores clave:
| Paso | Selector / Identificador |
|------|--------------------------|
| Enlaces Publicos | `img.wp-image-125438` o `img[src*="cxx"]` |
| Haz clic aqui | `div.text` con texto "Haz clic aqui" |
| CLIC AQUI PARA CONTINUAR | `button.button-s` |
| Primer resultado Google | `#search a[href]` (primer link) |
| Continuar (verificacion) | `button.button-s` con `initSystem()` |
| Anuncio obligatorio | `#click_message` + elemento de anuncio debajo |

## 📊 Progreso Actual

| Fase | Estado | Progreso |
|------|--------|----------|
| Mes 1: Fundamentos | ✅ Completado | 11/11 tareas |
| Mes 2: Visión Computacional | ⏳ Pendiente | 0/4 tareas |
| Mes 3: Evasión y Resiliencia | ⏳ Pendiente | 0/4 tareas |
| Mes 4: API & Architecture | ⏳ Pendiente | 0/3 tareas |
| Mes 5: Scaling & Docker | ⏳ Pendiente | 0/2 tareas |
| Mes 6: Demo & Polishing | ⏳ Pendiente | 0/3 tareas |

### Lo que ya funciona (v0.3):
- ✅ Arquitectura modular con sistema de adaptadores por sitio
- ✅ Motor de matching inteligente: rankea links por calidad/formato/proveedor (score 0-100)
- ✅ CLI con criterios de busqueda personalizables (`--quality`, `--format`, `--provider`)
- ✅ Soporte para **peliculasgd.net** (pipeline completo de 7 pasos con anti-bot)
- ✅ Soporte para **hackstore.mx** (extraccion directa de links con ranking)
- ✅ Simulacion de comportamiento humano (mouse, scroll, clicks)
- ✅ Manejo automatico de multiples pestanas, popups y redirects
- ✅ Anti-deteccion: User-Agent custom, flags de Chromium

### Nuevo en v0.3:
- **Busqueda inteligente**: "Quiero WEB-DL 1080p en uTorrent" → el agente lo encuentra
- **Multi-sitio**: Un solo comando funciona en peliculasgd.net y hackstore.mx
- **Extensible**: Agregar nuevos sitios = crear 1 archivo adaptador
- **README completo** con ejemplos de uso

### Siguiente paso:
- Testear ambos adaptadores con sitios reales
- Ajustar selectores de hackstore.mx segun estructura real de la pagina
- Considerar agregar vision computacional (GPT-4o Vision) para detectar botones fake

## 🚀 Inicio Rápido

```bash
# Instalar dependencias
pip install -r requirements.txt
playwright install

# Uso basico
python src/main.py <url-de-la-pelicula>

# Con criterios de busqueda (NUEVO en v0.3)
python src/main.py https://hackstore.mx/peliculas/eragon-2006 \
  --quality 1080p \
  --format WEB-DL \
  --provider utorrent

# Ver ayuda completa
python src/main.py --help
```

Ver [README.md](README.md) para mas ejemplos y documentacion completa.

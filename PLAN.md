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

### Mes 1: The "Wake Up" Phase (Fundamentos) 🟢
- [x] Configurar entorno (Python, Playwright, dotenv).
- [x] Implementar **Playwright** básico para abrir `peliculasgd.net` (`src/main.py`).
- [x] Crear lógica de navegación basada en selectores CSS simples.
- [x] Mapear y documentar flujo completo de navegación (7 pasos, multiples pestañas).
- [x] Implementar simulación de comportamiento humano (`src/human_sim.py`).
- [x] Implementar pipeline completo: película -> enlaces publicos -> intermediarios -> Google -> verificación -> link final.
- [ ] **Hito:** El script puede navegar desde una película hasta el link final (testing en progreso).

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
| Mes 1: Fundamentos | 🔧 En progreso | 6/7 tareas |
| Mes 2: Visión Computacional | ⏳ Pendiente | 0/4 tareas |
| Mes 3: Evasión y Resiliencia | ⏳ Pendiente | 0/4 tareas |
| Mes 4: API & Architecture | ⏳ Pendiente | 0/3 tareas |
| Mes 5: Scaling & Docker | ⏳ Pendiente | 0/2 tareas |
| Mes 6: Demo & Polishing | ⏳ Pendiente | 0/3 tareas |

### Lo que ya funciona:
- Entorno configurado con Python + Playwright
- Script base (`src/main.py`) con pipeline de 7 pasos para navegar desde pelicula hasta link final
- Simulacion de comportamiento humano (`src/human_sim.py`): mouse moves, scroll, clicks aleatorios
- Manejo automatico de multiples pestanas (abrir nuevas, cerrar popups no deseados)
- User-Agent personalizado y flags anti-deteccion de Chromium
- Screenshots de debug en cada paso para diagnostico

### Siguiente paso:
- Testear el flujo completo con peliculasgd.net y ajustar selectores segun sea necesario
- Los selectores de anuncios (Step 6) probablemente necesiten afinarse con la pagina real

## 🚀 Inicio Rápido

```bash
# Instalar dependencias
pip install playwright openai python-dotenv
playwright install

# Ejecutar primera prueba
python src/main.py
```

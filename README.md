# Neo-Link-Resolver

> "There is no spoon... and there are no ads."

Agente de navegacion autonomo que resuelve enlaces "sucios" (con acortadores, ads, anti-bots) hasta el link final de descarga/streaming. Soporta multiples sitios y busqueda inteligente por criterios.

## Caracteristicas

- **Interfaz Grafica (NUEVO v0.4)**: GUI moderna con logs en tiempo real y visualizacion del proceso
- **Multi-sitio**: Adaptadores para `peliculasgd.net`, `hackstore.mx` (extensible)
- **Busqueda inteligente**: Filtra por calidad (1080p, 720p), formato (WEB-DL, BluRay), proveedor (uTorrent, Google Drive, Mega)
- **Evasion anti-bot**: Simulacion de comportamiento humano (mouse, scroll, clicks aleatorios)
- **Automatizacion completa**: Maneja popups, redirects, verificaciones humanas y anuncios obligatorios

## Instalacion

```bash
# Clonar el repositorio
git clone https://github.com/JuanCamacho198/Neo-Link-Resolver.git
cd Neo-Link-Resolver

# Instalar dependencias
pip install -r requirements.txt

# Instalar navegadores de Playwright
playwright install
```

## Uso

### Interfaz Grafica (Recomendado)

La forma mas facil de usar Neo-Link-Resolver es con la interfaz grafica:

```bash
python src/gui.py
```

Esto abrira automaticamente un navegador en `http://localhost:8080` con una interfaz moderna donde puedes:

- Pegar la URL de la pelicula
- Seleccionar calidad, formato y proveedores preferidos
- **Ver en tiempo real** lo que el agente esta haciendo (logs en vivo)
- Copiar el link final con un click
- Abrir directamente el link de descarga

![GUI Preview](docs/gui-screenshot.png)

### Linea de Comandos (CLI)

Si prefieres la terminal:

```bash
python src/main.py <url-de-la-pelicula>
```

### Con criterios de busqueda

```bash
# Buscar WEB-DL 1080p en uTorrent
python src/main.py https://hackstore.mx/peliculas/eragon-2006 \
  --quality 1080p \
  --format WEB-DL \
  --provider utorrent

# Buscar 720p en Google Drive o Mega
python src/main.py https://www.peliculasgd.net/bob-esponja-... \
  --quality 720p \
  --provider drive.google mega
```

### Parametros disponibles

| Parametro | Descripcion | Default |
|-----------|-------------|---------|
| `--quality` | Calidad deseada: `2160p`, `1080p`, `720p`, `480p` | `1080p` |
| `--format` | Formato: `WEB-DL`, `BluRay`, `BRRip`, `HDRip`, etc | `WEB-DL` |
| `--provider` | Proveedores preferidos (puede ser multiple) | `utorrent drive.google` |
| `--language` | Idioma: `latino`, `español`, `english` | `latino` |
| `--headless` | Ejecutar en modo headless (sin GUI) | `False` |

## Ejemplos

### Con la GUI

1. Ejecuta `python src/gui.py`
2. En la interfaz:
   - Pega la URL: `https://hackstore.mx/peliculas/eragon-2006`
   - Selecciona calidad: `1080p`
   - Selecciona formato: `WEB-DL`
   - Selecciona proveedores: `uTorrent`, `Google Drive`
3. Click en "Resolver Link"
4. Observa en tiempo real como el agente navega
5. Cuando termine, copia el link final

### Con CLI

```bash
# peliculasgd.net - buscar mejor calidad disponible
python src/main.py https://www.peliculasgd.net/bob-esponja-en-busca-de-los-pantalones-cuadrados-2025-web-dl-1080p-latino-googledrive/

# hackstore.mx - 1080p WEB-DL en uTorrent
python src/main.py https://hackstore.mx/peliculas/eragon-2006 --quality 1080p --format WEB-DL --provider utorrent

# hackstore.mx - cualquier calidad, preferir Mega o Google Drive
python src/main.py https://hackstore.mx/peliculas/matrix-1999 --provider mega drive.google

# Modo headless (sin abrir ventana del navegador)
python src/main.py https://hackstore.mx/peliculas/inception-2010 --headless
```

## Arquitectura

```
src/
├── gui.py               # Interfaz grafica (NiceGUI) - NUEVO v0.4
├── main.py              # Entry point con CLI
├── resolver.py          # Wrapper del resolver con logging - NUEVO v0.4
├── logger.py            # Sistema de logging en tiempo real - NUEVO v0.4
├── config.py            # Configuracion global, criterios de busqueda
├── matcher.py           # Motor de ranking de links
├── human_sim.py         # Simulacion de comportamiento humano
└── adapters/            # Sistema de adaptadores por sitio
    ├── base.py          # Clase base abstracta
    ├── peliculasgd.py   # Adaptador para peliculasgd.net (7 pasos)
    └── hackstore.py     # Adaptador para hackstore.mx
```
src/
├── main.py              # Entry point con CLI
├── config.py            # Configuracion global, criterios de busqueda
├── matcher.py           # Motor de ranking de links
├── human_sim.py         # Simulacion de comportamiento humano
└── adapters/
    ├── base.py          # Clase base para adaptadores
    ├── peliculasgd.py   # Adaptador para peliculasgd.net (7 pasos)
    └── hackstore.py     # Adaptador para hackstore.mx
```

### Como funciona

1. **Seleccion de adaptador**: Segun la URL, se selecciona el adaptador apropiado
2. **Navegacion automatica**: El adaptador navega por los pasos necesarios (redirects, anti-bots, ads)
3. **Extraccion de links**: Se extraen todos los links de descarga disponibles
4. **Ranking inteligente**: El motor de matching rankea los links segun los criterios del usuario
5. **Resolucion final**: Se retorna el mejor link encontrado

## Sitios soportados

| Sitio | Estado | Complejidad |
|-------|--------|-------------|
| peliculasgd.net | ✅ Completo | Alta (7 pasos, anti-bot, ads) |
| hackstore.mx | ✅ Basico | Media (extraccion directa) |

## Roadmap

Ver [PLAN.md](PLAN.md) para el roadmap completo del proyecto.

## Contribuir

Para agregar soporte para un nuevo sitio:

1. Crear un nuevo adaptador en `src/adapters/nuevo_sitio.py` heredando de `SiteAdapter`
2. Implementar `can_handle(url)` y `resolve(url)`
3. Registrar el adaptador en `src/adapters/__init__.py`

## Licencia

MIT

## Disclaimer

Este proyecto es solo para fines educativos. El uso de este software para descargar contenido con derechos de autor puede ser ilegal en tu jurisdiccion.

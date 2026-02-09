# Tutorial: Usando la GUI de Neo-Link-Resolver

## Instalacion rapida

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Instalar navegadores de Playwright
playwright install

# 3. Lanzar la GUI
python src/gui.py
```

La interfaz se abrira automaticamente en tu navegador en `http://localhost:8080`

## Guia de uso paso a paso

### 1. Interfaz principal

Al abrir la GUI veras:

- **Header**: Logo y version
- **Descripcion**: Breve explicacion del proyecto
- **Formulario**: Campos para configurar la busqueda
- **Area de logs**: Consola en tiempo real (vacia al inicio)
- **Area de resultado**: Donde aparecera el link final

### 2. Configurar la busqueda

**URL de la pelicula:**
- Pega aqui el link completo de la pagina de la pelicula
- Ejemplo: `https://hackstore.mx/peliculas/eragon-2006`

**Calidad:**
- Selecciona la calidad deseada del dropdown
- Opciones: 2160p (4K), 1080p, 720p, 480p, 360p

**Formato:**
- Selecciona el formato preferido
- Opciones: WEB-DL, BluRay, BRRip, HDRip, DVDRip, CAMRip

**Proveedores preferidos:**
- Selecciona uno o mas proveedores
- Puedes hacer multi-seleccion (Ctrl+Click o Cmd+Click)
- Opciones: uTorrent, Google Drive, Mega, MediaFire, 1fichier

### 3. Resolver el link

1. Click en el boton **"Resolver Link"**
2. El spinner azul comenzara a girar
3. **Observa el area de logs** - aqui veras en tiempo real:
   - Que adaptador se esta usando
   - Cada paso que el agente ejecuta
   - Navegacion por las paginas
   - Deteccion de links
   - Ranking de opciones

**Colores de los logs:**
- 🔵 Azul: Informacion general
- 🟢 Verde: Exito (link encontrado, operacion completada)
- 🟡 Amarillo: Advertencias
- 🔴 Rojo: Errores
- 🟣 Morado: Pasos del proceso (STEP 1, STEP 2, etc)

### 4. Obtener el resultado

Cuando termine (puede tomar 30-90 segundos dependiendo del sitio):

**Si fue exitoso:**
- Veras "Resolucion exitosa!" en verde
- El link de descarga aparecera en un campo de texto
- Botones disponibles:
  - **Copiar Link**: Copia el link al portapapeles
  - **Abrir en navegador**: Abre el link directamente
- Detalles del resultado:
  - Proveedor (uTorrent, Google Drive, etc)
  - Calidad detectada (1080p, 720p, etc)
  - Formato detectado (WEB-DL, BluRay, etc)
  - Score (0-100): que tan bien matchea tus criterios

**Si fallo:**
- Veras "No se pudo resolver el link" en rojo
- Revisa los logs para ver donde fallo el proceso
- Puede ser que:
  - La URL no sea soportada
  - Los selectores del sitio hayan cambiado
  - El sitio este caido o bloqueado

### 5. Resolver otro link

Simplemente cambia la URL y los criterios, y click en "Resolver Link" de nuevo.

Puedes usar el boton de "basurero" en el area de logs para limpiarlos entre resoluciones.

## Tips y trucos

### Ver el navegador en accion

Por defecto, la GUI ejecuta el navegador en modo visible (headless=False), asi que veras una ventana de Chrome automatizada navegando por los sitios. Esto es util para:
- Entender que esta haciendo el agente
- Debuggear problemas
- Ver los anuncios y redirects que esta evadiendo

### Mejores resultados

- **peliculasgd.net**: Funciona mejor con links directos de peliculas especificas
- **hackstore.mx**: Usa los criterios de calidad/formato para filtrar entre las muchas opciones

### Velocidad

- **peliculasgd.net**: Tarda mas (~60-90s) por el flujo anti-bot de 7 pasos
- **hackstore.mx**: Mas rapido (~10-30s) con extraccion directa

### Logs muy largos

Si los logs ocupan mucho espacio, usa el boton de basurero para limpiarlos. El historial completo se mantiene en segundo plano.

## Problemas comunes

**"No adapter found for URL"**
- La URL no es de un sitio soportado (peliculasgd.net o hackstore.mx)

**"Could not resolve link"**
- El sitio puede haber cambiado su estructura
- Verifica los logs para ver en que paso fallo

**El navegador se cierra antes de tiempo**
- Puede ser un timeout. Los sitios muy lentos pueden exceder los tiempos de espera

**"Link not resolved" en peliculasgd.net**
- El flujo completo funciono pero no se encontro el link final en la pagina intermedia
- Revisa `peliculasgd_final_debug.png` generado automaticamente

## Siguiente nivel

Una vez familiarizado con la GUI, puedes:
- Usar el CLI para scripting: `python src/main.py <url> --quality 1080p`
- Agregar nuevos adaptadores para otros sitios (ver `src/adapters/base.py`)
- Contribuir al proyecto en GitHub

Disfruta resolviendo links sin ads!

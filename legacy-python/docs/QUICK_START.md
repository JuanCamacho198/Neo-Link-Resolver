# 🚀 Quick Start - Neo-Link-Resolver

## Instalación Rápida

```bash
# 1. Navega al directorio del proyecto
cd Neo-Link-Resolver

# 2. Crea un entorno virtual (recomendado)
python -m venv venv

# 3. Activa el entorno virtual
# En Windows:
venv\Scripts\activate

# 4. Instala las dependencias
pip install -r requirements.txt
```

## Ejecutar la GUI

```bash
# Desde la raíz del proyecto (Neo-Link-Resolver/)
python src/gui_desktop.py
```

La aplicación de escritorio se abrirá inmediatamente.

## Flujo de Uso

### Paso 1: Detectar Calidades
1. Ingresa una URL de película (ej: `https://hackstore.mx/peliculas/matrix-1999`)
2. Haz click en **"Detectar Calidades"**
3. Verás un spinner 🔄 + barra de progreso
4. Se mostrarán automáticamente las calidades disponibles

### Paso 2: Resolver Link
1. Se muestra automáticamente **"Paso 2"** con opciones
2. Selecciona tu **Calidad** preferida
3. Selecciona tu **Formato** preferido
4. Selecciona tus **Proveedores** preferidos
5. Haz click en **"Resolver Link"**

### Paso 3: Ver Resultado
- Se mostrarán automáticamente:
  - 📹 **Visualización** (screenshots)
  - 📋 **Logs** (detalles de lo que pasó)
  - ✅ **Resultado Final** (link + detalles)

## Requisitos

- Python 3.8+
- Chromium (se descarga automáticamente)
- 500MB de espacio libre

## Características v0.4.5

✅ Detección automática de calidades
✅ Logs y screenshots se muestran solo cuando necesitas
✅ Interface limpia y organizada
✅ Spinner + barra de progreso visible
✅ Manejo robusto de errores
✅ Retry automático con exponential backoff

---

¿Listo? Ejecuta `python src/gui_desktop.py`🎬

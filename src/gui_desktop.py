import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import os
import threading
import queue
import webbrowser

# Agregar el directorio actual (src) al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from resolver import LinkResolver
from quality_detector import QualityDetector
from history_manager import HistoryManager
from logger import get_logger

class NeoLinkResolverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Neo-Link-Resolver v0.6 (Desktop Edition)")
        self.root.geometry("950x750")
        
        # Configurar grid layout principal
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Estado de la aplicación
        self.detected_qualities = []
        self.log_queue = queue.Queue()
        self.is_working = False
        
        # Logger
        self.logger = get_logger()
        self.logger.register_callback(self.log_callback)
        
        # Construir UI
        self._build_ui()
        
        # Iniciar loop de logs
        self.root.after(100, self.process_log_queue)

    def log_callback(self, level, message):
        """Callback seguro para hilos"""
        self.log_queue.put(f"[{level}] {message}")

    def process_log_queue(self):
        """Procesa los mensajes de log en el hilo principal de UI"""
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_area.insert(tk.END, msg + "\n")
            # Auto-scroll si está al final
            self.log_area.see(tk.END)
        self.root.after(100, self.process_log_queue)

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        main_frame.columnconfigure(0, weight=1)

        # === SECCIÓN 1: INPUT ===
        input_frame = ttk.LabelFrame(main_frame, text="1. Configuración de Búsqueda", padding="10")
        input_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="URL Película:").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar()
        entry_url = ttk.Entry(input_frame, textvariable=self.url_var)
        entry_url.grid(row=0, column=1, sticky="ew", padx=10)
        
        self.btn_detect = ttk.Button(input_frame, text="🔍 Detectar Calidades", command=self.start_detection)
        self.btn_detect.grid(row=0, column=2)

        # Opciones avanzadas (Checkboxes)
        opts_frame = ttk.Frame(input_frame)
        opts_frame.grid(row=1, column=0, columnspan=3, sticky="w", pady=5)
        
        self.block_ads_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text="Bloquear Anuncios", variable=self.block_ads_var).pack(side=tk.LEFT, padx=5)
        
        self.speed_timer_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text="Acelerar Timers", variable=self.speed_timer_var).pack(side=tk.LEFT, padx=5)

        # === SECCIÓN 2: SELECCIÓN ===
        select_frame = ttk.LabelFrame(main_frame, text="2. Opciones de Descarga", padding="10")
        select_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        ttk.Label(select_frame, text="Calidad:").grid(row=0, column=0, padx=5)
        self.quality_combo = ttk.Combobox(select_frame, state="readonly", width=30)
        self.quality_combo.grid(row=0, column=1, padx=5)
        
        ttk.Label(select_frame, text="Proveedores:").grid(row=0, column=2, padx=5)
        self.provider_combo = ttk.Combobox(select_frame, state="readonly", width=30)
        self.provider_combo['values'] = ('MediaFire', 'MEGA', 'Google Drive', 'Torrent', 'Todos')
        self.provider_combo.current(0)
        self.provider_combo.grid(row=0, column=3, padx=5)

        self.btn_resolve = ttk.Button(select_frame, text="🚀 RESOLVER LINK", command=self.start_resolution, state="disabled")
        self.btn_resolve.grid(row=0, column=4, padx=10, sticky="e")

        # === SECCIÓN 3: RESULTADOS ===
        result_frame = ttk.LabelFrame(main_frame, text="3. Resultado Final", padding="10")
        result_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        result_frame.columnconfigure(0, weight=1)

        self.result_var = tk.StringVar(value="Esperando resolución...")
        self.entry_result = ttk.Entry(result_frame, textvariable=self.result_var, font=('Consolas', 10))
        self.entry_result.grid(row=0, column=0, sticky="ew", padx=5)
        
        btn_copy = ttk.Button(result_frame, text="📋 Copiar", command=self.copy_to_clipboard)
        btn_copy.grid(row=0, column=1, padx=2)
        
        btn_open = ttk.Button(result_frame, text="🌐 Abrir", command=self.open_result)
        btn_open.grid(row=0, column=2, padx=2)

        # === SECCIÓN 4: LOGS ===
        log_frame = ttk.LabelFrame(main_frame, text="Logs del Sistema", padding="5")
        log_frame.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)
        main_frame.rowconfigure(3, weight=1) # Logs expand vertical

        self.log_area = scrolledtext.ScrolledText(log_frame, state='normal', height=10, font=('Consolas', 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)
        # Configurar tags de colores para logs (básico)
        self.log_area.tag_config('INFO', foreground='black')
        self.log_area.tag_config('ERROR', foreground='red')

        # Status Bar
        self.status_var = tk.StringVar(value="Listo.")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=1, column=0, sticky="ew")

    # --- LÓGICA ---
    
    def copy_to_clipboard(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.result_var.get())
        self.status_var.set("Link copiado al portapapeles")

    def open_result(self):
        url = self.result_var.get()
        if url.startswith("http"):
            webbrowser.open(url)

    def toggle_inputs(self, enable):
        state = "normal" if enable else "disabled"
        self.btn_detect['state'] = state
        self.btn_resolve['state'] = state
        # El input de URL lo dejamos habilitado por comodidad

    def start_detection(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Error", "Ingresa una URL primero")
            return
        
        self.status_var.set("Detectando calidades...")
        self.toggle_inputs(False)
        self.log_area.delete(1.0, tk.END)
        self.logger.info(f"Iniciando detección para: {url}")
        
        # Ejecutar en hilo separado
        threading.Thread(target=self._run_detection, args=(url,), daemon=True).start()

    def _run_detection(self, url):
        try:
            detector = QualityDetector(headless=True)
            qualities = detector.detect_qualities(url)
            
            # Actualizar UI en hilo principal
            self.root.after(0, lambda: self._on_detection_complete(qualities))
        except Exception as e:
            self.logger.error(f"Error en detección: {e}")
            self.root.after(0, lambda: self._on_detection_error(str(e)))

    def _on_detection_complete(self, qualities):
        self.detected_qualities = qualities
        options = [q['display'] for q in qualities]
        
        if not options:
            options = ["1080p WEB-DL (Default)"]
            self.detected_qualities = [{"display": "1080p WEB-DL (Default)", "quality": "1080p"}]
            
        self.quality_combo['values'] = options
        self.quality_combo.current(0)
        
        self.status_var.set(f"Detección completada: {len(qualities)} opciones encontradas.")
        self.toggle_inputs(True)
        self.btn_resolve['state'] = "normal" # Habilitar resolver

    def _on_detection_error(self, error_msg):
        messagebox.showerror("Error de Detección", error_msg)
        self.status_var.set("Error en detección.")
        self.toggle_inputs(True)

    def start_resolution(self):
        url = self.url_var.get().strip()
        selected_disp = self.quality_combo.get()
        
        # Buscar objeto de calidad seleccionado
        q_data = next((q for q in self.detected_qualities if q['display'] == selected_disp), 
                      {"quality": "1080p", "format": "WEB-DL"})
        
        provider_sel = self.provider_combo.get()
        providers = [provider_sel] if provider_sel != 'Todos' else None
        
        self.status_var.set("Resolviendo enlace... Esto puede tardar unos segundos.")
        self.toggle_inputs(False)
        self.entry_result.delete(0, tk.END)
        self.logger.clear()
        
        # Ejecutar en hilo
        threading.Thread(
            target=self._run_resolution, 
            args=(url, q_data.get("quality", "1080p"), q_data.get("format", ""), providers),
            daemon=True
        ).start()

    def _run_resolution(self, url, quality, fmt, providers):
        try:
            resolver = LinkResolver(headless=False)
            resolver.use_network_interception = self.block_ads_var.get()
            resolver.accelerate_timers = self.speed_timer_var.get()
            
            result = resolver.resolve(url, quality=quality, format_type=fmt, providers=providers)
            
            self.root.after(0, lambda: self._on_resolution_complete(result))
        except Exception as e:
             self.logger.error(f"Error fatal: {e}")
             self.root.after(0, lambda: self.toggle_inputs(True))

    def _on_resolution_complete(self, result):
        self.toggle_inputs(True)
        if result and result.url and result.url != "LINK_NOT_RESOLVED":
            self.result_var.set(result.url)
            self.status_var.set("¡Éxito! Enlace resuelto.")
            messagebox.showinfo("Éxito", f"Link resuelto correctamente:\n\n{result.url}")
        else:
            self.result_var.set("No se pudo resolver")
            self.status_var.set("Falló la resolución. Revisa los logs.")
            messagebox.showerror("Falló", "No se pudo extraer el enlace final. Verifica los logs para ver por qué.")

def main():
    root = tk.Tk()
    # Estilo visual básico
    style = ttk.Style()
    style.theme_use('clam') 
    
    app = NeoLinkResolverApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

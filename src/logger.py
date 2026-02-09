"""
logger.py - Sistema de logging centralizado con soporte para GUI.
Permite capturar logs en tiempo real y enviarlos a callbacks.
"""

import sys
from typing import Callable, List
from datetime import datetime


class ResolverLogger:
    """
    Logger que captura todos los mensajes de print() del resolver
    y los envia a callbacks registrados (como una GUI).
    """

    def __init__(self):
        self.callbacks: List[Callable[[str, str], None]] = []
        self.logs: List[dict] = []

    def register_callback(self, callback: Callable[[str, str], None]):
        """
        Registra un callback que sera llamado con cada nuevo log.
        Firma: callback(level: str, message: str)
        """
        self.callbacks.append(callback)

    def log(self, level: str, message: str, step: str = None):
        """
        Registra un mensaje de log.
        level: "INFO", "SUCCESS", "WARNING", "ERROR", "STEP"
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Formato del mensaje
        if step:
            formatted = f"[{timestamp}] [{step}] {message}"
        else:
            formatted = f"[{timestamp}] {message}"

        # Guardar en historial
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "step": step,
            "formatted": formatted,
        }
        self.logs.append(log_entry)

        # Notificar a todos los callbacks
        for callback in self.callbacks:
            try:
                callback(level, formatted)
            except Exception as e:
                print(f"Error in logger callback: {e}", file=sys.stderr)

    def info(self, message: str, step: str = None):
        self.log("INFO", message, step)

    def success(self, message: str, step: str = None):
        self.log("SUCCESS", message, step)

    def warning(self, message: str, step: str = None):
        self.log("WARNING", message, step)

    def error(self, message: str, step: str = None):
        self.log("ERROR", message, step)

    def step(self, step_name: str, message: str):
        self.log("STEP", message, step_name)

    def clear(self):
        """Limpia el historial de logs."""
        self.logs.clear()

    def get_logs(self) -> List[dict]:
        """Retorna todos los logs registrados."""
        return self.logs.copy()


# Instancia global
_global_logger = ResolverLogger()


def get_logger() -> ResolverLogger:
    """Obtiene la instancia global del logger."""
    return _global_logger

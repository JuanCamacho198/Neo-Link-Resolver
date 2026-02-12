"""
adapters/base.py - Clase base para adaptadores de sitios.
Cada sitio tiene su propio adaptador que sabe como navegar y extraer links.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from playwright.sync_api import Page, BrowserContext
from config import SearchCriteria
from matcher import LinkOption


class SiteAdapter(ABC):
    """
    Clase base para adaptadores de sitios especificos.
    Cada sitio (peliculasgd, hackstore, etc) tendra su propio adaptador.
    """

    def __init__(self, context: BrowserContext, criteria: SearchCriteria):
        self.context = context
        self.criteria = criteria
        self.network_analyzer = None
        self.dom_analyzer = None
        self.timer_interceptor = None
        self.vision_resolver = None  # Nuevo: Sistema de visión como fallback

    def set_analyzers(self, network_analyzer=None, dom_analyzer=None, timer_interceptor=None, vision_resolver=None):
        """Asigna los analizadores para uso en el adaptador."""
        self.network_analyzer = network_analyzer
        self.dom_analyzer = dom_analyzer
        self.timer_interceptor = timer_interceptor
        self.vision_resolver = vision_resolver

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """
        Retorna True si este adaptador puede manejar la URL dada.
        Ejemplo: "peliculasgd.net" in url
        """
        pass

    @abstractmethod
    def resolve(self, url: str) -> LinkOption:
        """
        Navega desde la URL inicial hasta el link final,
        aplicando los criterios de busqueda.
        Retorna el mejor LinkOption encontrado.
        """
        pass

    def log(self, step: str, msg: str):
        """Helper para logging consistente."""
        print(f"  [{self.name()}:{step}] {msg}")

    @abstractmethod
    def name(self) -> str:
        """Retorna el nombre del adaptador (ej: "PeliculasGD", "Hackstore")."""
        pass

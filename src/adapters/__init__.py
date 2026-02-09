"""
adapters/__init__.py - Registry de adaptadores.
"""

from .base import SiteAdapter
from .peliculasgd import PeliculasGDAdapter
from .hackstore import HackstoreAdapter

# Registry de todos los adaptadores disponibles
ADAPTERS = [
    PeliculasGDAdapter,
    HackstoreAdapter,
]


def get_adapter(url: str, context, criteria):
    """
    Retorna el adaptador apropiado para la URL dada.
    """
    for adapter_class in ADAPTERS:
        # Instanciar temporalmente para check
        temp = adapter_class(context, criteria)
        if temp.can_handle(url):
            return temp

    raise ValueError(f"No adapter found for URL: {url}")

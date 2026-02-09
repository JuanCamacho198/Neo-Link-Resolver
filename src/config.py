"""
config.py - Configuracion global del Neo-Link-Resolver.
Criterios de busqueda, proveedores soportados, constantes.
"""

from typing import List
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Tipos de calidad soportados (ordenados por prioridad)
# ---------------------------------------------------------------------------
QUALITY_PRIORITY = [
    "2160p",  # 4K
    "1080p",  # Full HD
    "720p",   # HD
    "480p",   # SD
    "360p",   # Low
]

# Formatos soportados (ordenados por preferencia general)
FORMAT_PRIORITY = [
    "WEB-DL",
    "BluRay",
    "BRRip",
    "HDRip",
    "DVDRip",
    "CAMRip",
    "TS",
]

# Proveedores de descarga (ordenados por preferencia general)
PROVIDER_PRIORITY = [
    "utorrent",      # Torrents
    "drive.google",  # Google Drive
    "mega",          # Mega.nz
    "mediafire",     # Mediafire
    "1fichier",      # 1fichier
    "uptobox",       # Uptobox
    "other",         # Cualquier otro
]


# ---------------------------------------------------------------------------
# Criterios de busqueda
# ---------------------------------------------------------------------------
@dataclass
class SearchCriteria:
    """
    Define que esta buscando el usuario.
    Ejemplo:
        SearchCriteria(
            quality="1080p",
            format="WEB-DL",
            preferred_providers=["utorrent", "drive.google"]
        )
    """
    quality: str = None           # "1080p", "720p", etc.
    format: str = None            # "WEB-DL", "BluRay", etc.
    preferred_providers: List[str] = None  # ["utorrent", "mega"]
    language: str = "latino"      # "latino", "español", "english"

    def __post_init__(self):
        if self.preferred_providers is None:
            self.preferred_providers = ["utorrent", "drive.google"]

    def matches_quality(self, text: str) -> bool:
        """Retorna True si el texto contiene la calidad buscada."""
        if not self.quality:
            return True
        return self.quality.lower() in text.lower()

    def matches_format(self, text: str) -> bool:
        """Retorna True si el texto contiene el formato buscado."""
        if not self.format:
            return True
        return self.format.lower() in text.lower()

    def matches_language(self, text: str) -> bool:
        """Retorna True si el texto contiene el idioma buscado."""
        if not self.language:
            return True
        return self.language.lower() in text.lower()

    def score_provider(self, provider_name: str) -> int:
        """
        Retorna un score (0-100) basado en que tan preferido es el proveedor.
        Mayor score = mas preferido.
        """
        provider_lower = provider_name.lower()
        for i, preferred in enumerate(self.preferred_providers):
            if preferred.lower() in provider_lower:
                # Los primeros en la lista tienen mayor score
                return 100 - (i * 10)
        # Si no esta en preferred, score bajo pero no cero
        return 10


# ---------------------------------------------------------------------------
# Constantes de navegacion
# ---------------------------------------------------------------------------
TIMEOUT_NAV = 60_000       # 60s para navegaciones
TIMEOUT_ELEMENT = 15_000   # 15s para esperar elementos
AD_WAIT_SECONDS = 45       # Espera despues de click en anuncio

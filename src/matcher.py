"""
matcher.py - Motor de ranking de links segun criterios del usuario.
Encuentra el mejor link entre multiples opciones.
"""

from dataclasses import dataclass
from typing import List
from config import SearchCriteria, QUALITY_PRIORITY, FORMAT_PRIORITY, PROVIDER_PRIORITY


@dataclass
class LinkOption:
    """Representa un link de descarga encontrado."""
    url: str
    text: str          # Texto del link o descripcion
    provider: str      # "utorrent", "drive.google", etc.
    quality: str = ""  # "1080p", "720p", etc.
    format: str = ""   # "WEB-DL", "BluRay", etc.
    score: float = 0.0

    def __repr__(self):
        return f"LinkOption(provider={self.provider}, quality={self.quality}, format={self.format}, score={self.score:.1f})"


class LinkMatcher:
    """
    Rankea links segun los criterios del usuario.
    """

    def __init__(self, criteria: SearchCriteria):
        self.criteria = criteria

    def parse_link(self, url: str, text: str) -> LinkOption:
        """
        Parsea un link y extrae informacion (proveedor, calidad, formato).
        """
        text_lower = text.lower()
        url_lower = url.lower()
        combined = f"{text_lower} {url_lower}"

        # Detectar proveedor
        provider = "other"
        for p in PROVIDER_PRIORITY:
            if p in url_lower:
                provider = p
                break

        # Detectar calidad
        quality = ""
        for q in QUALITY_PRIORITY:
            if q.lower() in combined:
                quality = q
                break

        # Detectar formato
        format_type = ""
        for f in FORMAT_PRIORITY:
            if f.lower() in combined:
                format_type = f
                break

        return LinkOption(
            url=url,
            text=text,
            provider=provider,
            quality=quality,
            format=format_type,
        )

    def score_link(self, link: LinkOption) -> float:
        """
        Asigna un score a un link basado en que tan bien matchea los criterios.
        Score range: 0-100 (mayor es mejor).
        """
        score = 0.0

        # +40 pts: Match de calidad exacta
        if self.criteria.quality and link.quality:
            if self.criteria.quality.lower() == link.quality.lower():
                score += 40
            else:
                # Penalizacion si la calidad es diferente
                score -= 10

        # +30 pts: Match de formato exacto
        if self.criteria.format and link.format:
            if self.criteria.format.lower() == link.format.lower():
                score += 30
            else:
                score -= 5

        # +30 pts: Proveedor preferido (scoring dinamico)
        provider_score = self.criteria.score_provider(link.provider)
        score += (provider_score / 100) * 30

        # Bonus: link contiene idioma deseado
        if self.criteria.matches_language(link.text):
            score += 10

        return max(0.0, score)  # No scores negativos

    def rank_links(self, links: List[LinkOption]) -> List[LinkOption]:
        """
        Rankea una lista de links y los retorna ordenados por score.
        """
        for link in links:
            link.score = self.score_link(link)

        # Ordenar por score descendente
        ranked = sorted(links, key=lambda x: x.score, reverse=True)
        return ranked

    def find_best_link(self, links: List[LinkOption]) -> LinkOption:
        """
        Retorna el mejor link segun los criterios.
        """
        if not links:
            return None

        ranked = self.rank_links(links)
        return ranked[0]

    def parse_and_rank(self, raw_links: List[dict]) -> List[LinkOption]:
        """
        Convierte links crudos (dict con 'url' y 'text') en LinkOptions
        y los rankea.
        raw_links = [{"url": "...", "text": "..."}, ...]
        """
        options = [self.parse_link(lnk["url"], lnk["text"]) for lnk in raw_links]
        return self.rank_links(options)

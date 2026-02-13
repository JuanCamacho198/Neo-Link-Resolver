"""
url_parser.py - Utilidades para parsear información de URLs
"""

import re
from typing import Dict, Optional


def extract_metadata_from_url(url: str) -> Dict[str, Optional[str]]:
    """
    Extrae metadata (calidad, formato, idioma) de una URL de película.
    
    Ejemplos:
        https://www.peliculasgd.net/la-empleada-2025-web-dl-1080p-latino-googledrive/
        -> {'quality': '1080p', 'format': 'WEB-DL', 'language': 'latino'}
        
        https://hackstore.mx/peliculas/interstellar-2014-bluray-1080p
        -> {'quality': '1080p', 'format': 'BluRay', 'language': None}
    
    Args:
        url: URL de la película
        
    Returns:
        Dict con 'quality', 'format', 'language' (o None si no se detecta)
    """
    url_lower = url.lower()
    
    metadata = {
        'quality': None,
        'format': None,
        'language': None
    }
    
    # Detectar calidad (1080p, 720p, 480p, 4k, 2160p, etc)
    quality_patterns = [
        r'\b(2160p|4k)\b',
        r'\b(1080p)\b',
        r'\b(720p)\b',
        r'\b(480p)\b',
        r'\b(360p)\b'
    ]
    
    for pattern in quality_patterns:
        match = re.search(pattern, url_lower)
        if match:
            metadata['quality'] = match.group(1).upper()
            if metadata['quality'] == '4K':
                metadata['quality'] = '2160p'
            break
    
    # Detectar formato (WEB-DL, BluRay, DVDRip, REMUX, etc)
    format_patterns = {
        r'\b(web-dl|webdl|web\.dl)\b': 'WEB-DL',
        r'\b(bluray|blu-ray|bdrip|brrip)\b': 'BluRay',
        r'\b(dvdrip|dvd-rip)\b': 'DVDRip',
        r'\b(remux)\b': 'REMUX',
        r'\b(webrip|web-rip)\b': 'WEBRip',
        r'\b(hdtv)\b': 'HDTV',
        r'\b(cam|camrip)\b': 'CAM',
        r'\b(ts|telesync)\b': 'TS',
        r'\b(hdrip)\b': 'HDRip'
    }
    
    for pattern, format_name in format_patterns.items():
        if re.search(pattern, url_lower):
            metadata['format'] = format_name
            break
    
    # Detectar idioma (latino, español, castellano, dual, inglés, sub)
    language_patterns = {
        r'\b(latino|lat)\b': 'latino',
        r'\b(español|castellano|esp|cast)\b': 'español',
        r'\b(dual|dual-latino)\b': 'dual',
        r'\b(inglés|english|eng|ingles)\b': 'inglés',
        r'\b(subtitulado|sub|subs)\b': 'subtitulado',
        r'\b(vose)\b': 'VOSE'
    }
    
    for pattern, lang_name in language_patterns.items():
        if re.search(pattern, url_lower):
            metadata['language'] = lang_name
            break
    
    return metadata


def should_override_criteria_from_url(url: str) -> bool:
    """
    Determina si la URL contiene metadata suficiente para overridear los criterios del usuario.
    
    Si la URL específica claramente calidad/formato (ej: peliculasgd con la calidad en el slug),
    entonces usar esa metadata en lugar de los criterios genéricos del usuario.
    
    Returns:
        True si la URL tiene metadata clara que debe usarse
    """
    metadata = extract_metadata_from_url(url)
    
    # Si tiene calidad Y formato, es muy específica
    if metadata['quality'] and metadata['format']:
        return True
    
    # Si es peliculasgd y tiene calidad (aunque no tenga formato claro)
    if 'peliculasgd.net' in url.lower() and metadata['quality']:
        return True
    
    return False

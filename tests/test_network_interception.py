"""
tests/test_network_interception.py - Pruebas para los nuevos módulos de interceptación.
"""

from src.network_analyzer import NetworkAnalyzer
from src.dom_analyzer import DOMAnalyzer

def test_network_analyzer_ad_detection():
    analyzer = NetworkAnalyzer()
    
    # Test ads
    assert analyzer.is_ad_url("https://doubleclick.net/ad") is True
    assert analyzer.is_ad_url("https://googlesyndication.com/pagead") is True
    
    # Test non-ads
    assert analyzer.is_ad_url("https://google.com/search") is False
    assert analyzer.is_ad_url("https://mega.nz/file/123") is False

def test_network_analyzer_download_detection():
    analyzer = NetworkAnalyzer()
    
    # Test download domains
    assert analyzer.is_download_url("https://mega.nz/file/abc") is True
    assert analyzer.is_download_url("https://drive.google.com/file/d/123") is True
    assert analyzer.is_download_url("https://mediafire.com/download/xyz") is True
    
    # Test non-download domains
    assert analyzer.is_download_url("https://not-a-download-site.com") is False

def test_dom_analyzer_score():
    analyzer = DOMAnalyzer()
    
    # Mock features for a "real" button
    real_features = {
        'display': 'block',
        'visibility': 'visible',
        'area': 5000,
        'position': 'static',
        'zIndex': 0,
        'classes': 'btn btn-primary',
        'id': 'download-btn',
        'opacity': 1.0,
        'text': 'Descargar Película',
        'href': 'https://mega.nz/file/123',
        'cursor': 'pointer'
    }
    
    score = analyzer.calculate_realness_score(real_features)
    assert score > 0.7
    
    # Mock features for an "ad" overlay
    ad_features = {
        'display': 'block',
        'visibility': 'visible',
        'area': 500000, # Muy grande
        'position': 'fixed',
        'zIndex': 9999,
        'classes': 'ad-overlay banner',
        'id': 'promo-1',
        'opacity': 0.8,
        'text': '¡Felicidades! Has ganado un iPhone',
        'href': 'https://doubleclick.net/click',
        'cursor': 'pointer'
    }
    
    score = analyzer.calculate_realness_score(ad_features)
    assert score < 0.4


from bs4 import BeautifulSoup
import json
import re

def analyze_hackstore_html(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    print("--- Analizando Botones 'Ver Enlaces' ---")
    buttons = soup.find_all(string=re.compile(r'Ver Enlaces', re.I))
    for i, btn in enumerate(buttons):
        parent = btn.parent
        print(f"Botón {i}: {parent.name} - Clases: {parent.get('class')} - Texto: {btn.strip()}")
        # Subir un par de niveles para ver el contenedor
        curr = parent
        for _ in range(3):
            if curr.parent:
                curr = curr.parent
                print(f"  Parent: {curr.name} - Clases: {curr.get('class')} - ID: {curr.get('id')}")
    
    print("\n--- Analizando Links Existentes ---")
    links = soup.find_all('a', href=True)
    potential_links = [l['href'] for l in links if any(p in l['href'] for p in ['mega', 'acortame', 'mediafire', 'ouo', 'zippyshare'])]
    print(f"Total links encontrados: {len(links)}")
    print(f"Links sospechosos (shorteners/providers): {len(potential_links)}")
    for l in potential_links[:10]:
        print(f"  - {l}")

    # Buscar el script que contiene la data de links (si existe)
    print("\n--- Buscando Bloques de Data ---")
    scripts = soup.find_all('script')
    for s in scripts:
        if s.string and ('qualities' in s.string or 'links' in s.string):
            print(f"Encontrado script con data (longitud: {len(s.string)})")
            # Guardar el script para análisis profundo
            with open('data/script_data.json', 'w', encoding='utf-8') as sf:
                sf.write(s.string)
            print("  Script guardado en 'data/script_data.json'")

if __name__ == "__main__":
    import os
    abs_path = os.path.abspath('data/hackstore_debug.html')
    analyze_hackstore_html(abs_path)

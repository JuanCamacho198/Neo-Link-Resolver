
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

    print("\n--- Analizando Secciones de Calidad ---")
    for tag in ['h1', 'h2', 'h3', 'h4']:
        for h in soup.find_all(tag):
            text = h.text.strip()
            if any(q in text.lower() for q in ['1080p', '720p', '4k', 'dvdrip']):
                print(f"Encontrado Heading: {text} ({tag})")
                print(f"  Parent: {h.parent.name} - Clases: {h.parent.get('class')}")
                
                # Buscar en el abuelo si es necesario
                container = h.parent
                print(f"  Container Content (primeros 200 chars): {container.text.strip()[:200]}...")
                
                # Buscar links dentro del contenedor del heading
                links = container.find_all('a')
                for a in links:
                    print(f"    Link en contenedor: {a.get('href')} - Texto: {a.text.strip()}")

                gp = h.parent.parent
                print(f"  Grandparent: {gp.name} - Clases: {gp.get('class')}")
# Ver todos los elementos hijos para entender qué son
                        for j, sub in enumerate(child.find_all(True, recursive=False)):
                            print(f"        Sub {j}: {sub.name} - Clases: {sub.get('class')} - HTML: {str(sub)[:100]}...")
                            # Ver descendientes que tengan href o texto
                            for k, desc in enumerate(sub.find_all(True)):
                                if desc.get('href'):
                                    print(f"          Desc {k}: {desc.name} - Href: {desc.get('href')}")
                                if desc.name == 'button':
                                    print(f"          Desc {k}: button - Text: {desc.text.strip()}")

if __name__ == "__main__":
    import os
    abs_path = os.path.abspath('data/hackstore_debug.html')
    analyze_hackstore_html(abs_path)

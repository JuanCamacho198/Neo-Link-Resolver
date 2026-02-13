import sys
from bs4 import BeautifulSoup

def find_provider_links(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Find the quality headings
    headings = soup.find_all('h3')
    for heading in headings:
        text = heading.get_text(strip=True)
        if '1080p' in text or '720p' in text:
            print(f"\n--- Heading: {text} ---")
            
            parent_container = heading.find_parent('div')
            if not parent_container: continue
            
            grandparent = parent_container.parent
            if not grandparent: continue
            
            rows_container = grandparent.find('div', class_='divide-y')
            if rows_container:
                for row in rows_container.find_all('div', recursive=False):
                    row_text = row.get_text(separator=' ', strip=True)
                    print(f"\n  Row: {row_text[:100]}...")
                    
                    # Print every tag inside the row and its attributes
                    all_elements = row.find_all(True)
                    for el in all_elements:
                        if el.name in ['div', 'span', 'p', 'svg', 'path']:
                            continue
                        print(f"    <{el.name}> attrs: {el.attrs}")
                        if el.name == 'button':
                            print(f"      Text: {el.get_text(strip=True)}")
            else:
                print("Could not find rows container (divide-y)")

if __name__ == "__main__":
    find_provider_links(r'c:\Users\Juan Camacho\Documents\PROYECTOS\Neo-Link-Resolver\data\hackstore_debug.html')

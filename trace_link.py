from bs4 import BeautifulSoup
import os

def check():
    abs_path = os.path.abspath('data/hackstore_debug.html')
    with open(abs_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Find the 1080p heading
    headings = [h for h in soup.find_all(['h3', 'h4']) if '1080p' in h.text]
    if not headings:
        print("No 1080p headings found")
        return
        
    h = headings[0]
    print(f"--- Heading found: {h.text.strip()} ---")
    
    # 2. Go up to grandparent
    gp = h.parent.parent
    print(f"Grandparent: <{gp.name}> Classes: {gp.get('class')}")
    
    # 3. Print siblings of the div that contains the heading
    print("\n--- Siblings of Heading Container (div level 1) ---")
    parent_div = h.parent
    for sib in parent_div.next_siblings:
        if sib.name:
            print(f"Sibling: <{sib.name}> Classes: {sib.get('class')}")
            print(sib.get_text()[:100])
            # Check for links or buttons
            for item in sib.find_all(['a', 'button']):
                print(f"  {item.name.upper()}: {item.get_text().strip()[:30]}")
                if item.name == 'a':
                    print(f"    HREF: {item.get('href')}")
                else:
                    print(f"    ATTRS: { {k:v for k,v in item.attrs.items() if k!='class'} }")

    # 4. Check the "flex" container that likely holds the table
    print("\n--- Searching for the 'Descargar' section ---")
    sections = gp.find_all('section')
    for s in sections:
        print(f"Section classes: {s.get('class')}")
        for row in s.find_all('div', recursive=False):
            print(f"  Row: {row.get_text().strip()[:50]}")
            for link in row.find_all('a', href=True):
                 print(f"    LINK: {link.get('href')} ({link.get_text().strip()})")
            for btn in row.find_all('button'):
                 print(f"    BUTTON: {btn.get_text().strip()} | Attrs: {btn.attrs}")

if __name__ == '__main__':
    check()

if __name__ == '__main__':
    check()

from bs4 import BeautifulSoup
import os

def analyze():
    abs_path = os.path.abspath('data/hackstore_debug.html')
    with open(abs_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Target common quality names
    targets = ['1080p', '720p', '4k', 'dvdrip']
    
    found_any = False
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        for h in soup.find_all(tag):
            text = h.get_text().strip().lower()
            if any(q in text for q in targets) and len(text) < 50:
                print(f"\n=======================================================")
                print(f"QUALITY HEADING: '{h.get_text().strip()}' (Tag: {h.name})")
                
                curr = h
                for i in range(5):
                    curr = curr.parent
                    if not curr: break
                    
                    print(f"Parent level {i+1}: {curr.name} (Classes: {curr.get('class')})")
                    # Look for everything that has a link or looks like a provider
                    items = curr.find_all(True) # All tags
                    for item in items:
                        item_text = item.get_text().strip()
                        # Keywords to identify provider rows/links
                        keywords = ['mega', 'mediafire', 'drive', '1fichier', 'uptobox', 'descargar', 'ver online']
                        if item.name == 'a' or item.name == 'button' or any(k in item_text.lower() for k in keywords):
                            if item.name in ['a', 'button']:
                                parent_a = item.find_parent('a')
                                attrs = {k: v for k, v in item.attrs.items() if k not in ['class', 'style']}
                                print(f"    {item.name.upper()}: {item_text[:30]} | Attrs: {attrs}")
                                if parent_a:
                                    print(f"      Wrapped in A: {parent_a.get('href')}")
                            elif 'mega' in item_text.lower() or 'mediafire' in item_text.lower():
                                # This might be a container for a provider
                                print(f"    CONTAINER ({item.name}): {item_text[:50]}")
                                # Look for links inside this container
                                for a in item.find_all('a'):
                                    print(f"      INTERNAL LINK: {a.get('href')} | Text: {a.get_text().strip()}")

    # Look for ALL links that might be interesting
    print("\n--- All Links matching 'acortame' or 'mega' ---")
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if any(k in href.lower() for k in ['acortame', 'mega', 'mediafire', '1fichier', 'uptobox', 'drive']):
            print(f"  LINK: {href} | Text: {a.get_text().strip()}")
            # Find the heading that is closest to this link (going backwards in the DOM)
            prev = a.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if prev:
                print(f"    Closest preceding heading: '{prev.get_text().strip()}'")

    # If no links found, check if they are in data attributes of buttons
    print("\n--- Checking Buttons for data-href or similar ---")
    for b in soup.find_all('button'):
        attrs = b.attrs
        if any(v and isinstance(v, str) and ('http' in v or 'acortame' in v) for v in attrs.values()):
            print(f"  BUTTON with link-like attr: {b.get_text().strip()} | Attrs: {attrs}")
            prev = b.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if prev:
                print(f"    Closest preceding heading: '{prev.get_text().strip()}'")

    # Check for script-based links
    print("\n--- Checking for links in scripts ---")
    import re
    scripts = soup.find_all('script')
    for s in scripts:
        if s.string:
            found = re.findall(r'https?://[^\s\"\'<>]+(?:acortame|mega|mediafire|1fichier|uptobox)[^\s\"\'<>]*', s.string)
            if found:
                print(f"  Links in script: {len(found)}")
                for f in found[:5]:
                    print(f"    FOUND: {f}")

    if not found_any:
        print("No quality headings found.")

if __name__ == '__main__':
    analyze()

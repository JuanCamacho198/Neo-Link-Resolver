import re
import os

def search_links(path):
    if not os.path.exists(path):
        print(f"Path does not exist: {path}")
        return
    
    print(f"Searching in: {path}")
    try:
        with open(path, 'rb') as f:
            # Read in chunks to avoid memory issues with large files
            chunk_size = 1024 * 1024
            while True:
                chunk = f.read(chunk_size)
                if not chunk: break
                
                # Look for URLs
                matches = re.findall(rb'https?://[a-zA-Z0-9.\-/?=&%_]+', chunk)
                for m in matches:
                    decoded = m.decode(errors='ignore')
                    if 'safez.es' in decoded or 'drive.google.com' in decoded or 'googledrive' in decoded:
                        print(f"FOUND: {decoded}")
    except Exception as e:
        print(f"Error: {e}")

# Search in history and local state
search_links('data/browser_profile/Default/History')
search_links('data/browser_profile/Local State')
search_links('data/browser_profile/Default/Preferences')

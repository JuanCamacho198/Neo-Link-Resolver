import base64
import re

def rot13(text):
    out = []
    for char in text:
        if 'a' <= char <= 'z':
            out.append(chr((ord(char) - ord('a') + 13) % 26 + ord('a')))
        elif 'A' <= char <= 'Z':
            out.append(chr((ord(char) - ord('A') + 13) % 26 + ord('A')))
        else:
            out.append(char)
    return ''.join(out)

def is_b64(text):
    if len(text) < 4: return False
    return re.match(r'^[a-zA-Z0-9+/]+={0,2}$', text) is not None

def check(text, label):
    if not text: return False
    # Common domains
    for domain in ['http', 'safez', 'google', 'drive', 'bit.ly', 'tulink', 'domk5']:
        if domain in text.lower():
            print(f"!!! MATCH !!! [{label}]: {text}")
            return True
    return False

def explore(text, depth=0, path=""):
    if depth > 4: return False
    
    # 1. As is
    if check(text, path): return True
    
    # 2. ROT13
    rt = rot13(text)
    if check(rt, path + " -> ROT13"): return True
    
    # 3. Reverse
    rev = text[::-1]
    if check(rev, path + " -> Reverse"): return True

    # 4. B64 Decode
    if is_b64(text):
        try:
            # Add padding just in case
            padded = text + ("=" * ((4 - len(text) % 4) % 4))
            decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
            if explore(decoded, depth + 1, path + " -> B64"): return True
        except: pass

    # 5. ROT13 then B64 Decode
    if is_b64(rt):
        try:
            padded = rt + ("=" * ((4 - len(rt) % 4) % 4))
            decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
            if explore(decoded, depth + 1, path + " -> ROT13 -> B64"): return True
        except: pass

    # 6. Reverse then B64 Decode
    rev_clean = re.sub(r'[^a-zA-Z0-9+/]', '', rev)
    if is_b64(rev_clean):
        try:
            padded = rev_clean + ("=" * ((4 - len(rev_clean) % 4) % 4))
            decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
            if explore(decoded, depth + 1, path + " -> Reverse -> B64"): return True
        except: pass

    return False

link_out = "UTZBWWJQaVQ4eUlrRG5pTjdnMkhVaUZHWko2U0wxK0tNd3A4RmN1T1dvS1RJM1JuS3hjejlZQy9qOHhwYW40MEVGQWxWdFNSVmxOUTZJcHJudTQvellTci8xeXU1blhENlhMZC9Ed1oxTS96Z3FIT2VYcWJaalZFd1RUV1cySjN1eUZwbEVuSFpJM0VIYU0xT1M5NzY2b0dsZ2NDSk1DOS9pQVRMTzQ0YmlhZWFIb0ZMOVlLVjZSRVBaeHVxWENyN1ROcHhVVURSeU1PcW5COFgydFYvMkZnd20xU0Z4MGp5Qlc1QWFvNnJkTCt6UTB5TU9LcW0wQzBhMk10Y3EyZ0E5YkJJc0dxaW8rNkhIamZWWkdXNkE9PQ=="

print("Starting deep exploration...")
explore(link_out)

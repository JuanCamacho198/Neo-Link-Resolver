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

def try_decode_recursive(text, depth=0):
    if depth > 5: return
    
    # Try plain B64
    if is_b64(text):
        try:
            decoded = base64.b64decode(text).decode('utf-8', errors='ignore')
            if 'http' in decoded.lower():
                print(f"FOUND at depth {depth} (B64): {decoded}")
                return True
            if try_decode_recursive(decoded, depth + 1): return True
        except: pass
        
    # Try ROT13
    rt = rot13(text)
    if 'http' in rt.lower():
        print(f"FOUND at depth {depth} (ROT13): {rt}")
        return True
    
    # Try ROT13 -> B64
    if is_b64(rt):
        try:
            decoded = base64.b64decode(rt).decode('utf-8', errors='ignore')
            if 'http' in decoded.lower():
                print(f"FOUND at depth {depth} (ROT13 -> B64): {decoded}")
                return True
            if try_decode_recursive(decoded, depth + 1): return True
        except: pass

    # Try B64 -> ROT13
    if is_b64(text):
        try:
            decoded = base64.b64decode(text).decode('utf-8', errors='ignore')
            rt = rot13(decoded)
            if 'http' in rt.lower():
                print(f"FOUND at depth {depth} (B64 -> ROT13): {rt}")
                return True
            if try_decode_recursive(rt, depth + 1): return True
        except: pass

    return False

link_out = "UTZBWWJQaVQ4eUlrRG5pTjdnMkhVaUZHWko2U0wxK0tNd3A4RmN1T1dvS1RJM1JuS3hjejlZQy9qOHhwYW40MEVGQWxWdFNSVmxOUTZJcHJudTQvellTci8xeXU1blhENlhMZC9Ed1oxTS96Z3FIT2VYcWJaalZFd1RUV1cySjN1eUZwbEVuSFpJM0VIYU0xT1M5NzY2b0dsZ2NDSk1DOS9pQVRMTzQ0YmlhZWFIb0ZMOVlLVjZSRVBaeHVxWENyN1ROcHhVVURSeU1PcW5COFgydFYvMkZnd20xU0Z4MGp5Qlc1QWFvNnJkTCt6UTB5TU9LcW0wQzBhMk10Y3EyZ0E5YkJJc0dxaW8rNkhIamZWWkdXNkE9PQ=="

print("Starting recursive search...")
try_decode_recursive(link_out)

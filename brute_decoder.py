import base64

def rot13(text):
    return "".join(chr((ord(c)-97+13)%26+97) if 'a'<=c<='z' else chr((ord(c)-65+13)%26+65) if 'A'<=c<='Z' else c for c in text)

def b64_decode(text):
    try:
        # Add padding
        text = text.strip()
        text += "=" * ((4 - len(text) % 4) % 4)
        return base64.b64decode(text).decode('utf-8', errors='ignore')
    except:
        return None

def find_target(text):
    for domain in ['safez', 'google', 'drive', 'bit.ly', 'tulink', 'domk5', 'http']:
        if domain in text.lower():
            return True
    return False

def solve(text, depth=0, path=""):
    if depth > 5: return
    
    # Try ROT13
    r = rot13(text)
    if find_target(r):
        print(f"FOUND: {r} at {path} -> ROT13")
        return True
    if solve(r, depth+1, path + " -> ROT13"): return True
    
    # Try B64
    b = b64_decode(text)
    if b:
        if find_target(b):
            print(f"FOUND: {b} at {path} -> B64")
            return True
        if solve(b, depth+1, path + " -> B64"): return True
    
    return False

link_out = "UTZBWWJQaVQ4eUlrRG5pTjdnMkhVaUZHWko2U0wxK0tNd3A4RmN1T1dvS1RJM1JuS3hjejlZQy9qOHhwYW40MEVGQWxWdFNSVmxOUTZJcHJudTQvellTci8xeXU1blhENlhMZC9Ed1oxTS96Z3FIT2VYcWJaalZFd1RUV1cySjN1eUZwbEVuSFpJM0VIYU0xT1M5NzY2b0dsZ2NDSk1DOS9pQVRMTzQ0YmlhZWFIb0ZMOVlLVjZSRVBaeHVxWENyN1ROcHhVVURSeU1PcW5COFgydFYvMkZnd20xU0Z4MGp5Qlc1QWFvNnJkTCt6UTB5TU9LcW0wQzBhMk10Y3EyZ0E5YkJJc0dxaW8rNkhIamZWWkdXNkE9PQ=="
solve(link_out)

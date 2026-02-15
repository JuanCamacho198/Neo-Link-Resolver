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

def xor_data(data, key):
    if isinstance(key, str): key = key.encode()
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))

link_out_b64 = 'UTZBWWJQaVQ4eUlrRG5pTjdnMkhVaUZHWko2U0wxK0tNd3A4RmN1T1dvS1RJM1JuS3hjejlZQy9qOHhwYW40MEVGQWxWdFNSVmxOUTZJcHJudTQvellTci8xeXU1blhENlhMZC9Ed1oxTS96Z3FIT2VYcWJaalZFd1RUV1cySjN1eUZwbEVuSFpJM0VIYU0xT1M5NzY2b0dsZ2NDSk1DOS9pQVRMTzQ0YmlhZWFIb0ZMOVlLVjZSRVBaeHVxWENyN1ROcHhVVURSeU1PcW5COFgydFYvMkZnd20xU0Z4MGp5Qlc1QWFvNnJkTCt6UTB5TU9LcW0wQzBhMk10Y3EyZ0E5YkJJc0dxaW8rNkhIamZWWkdXNkE9PQ=='
api_key = 'f866376a065f79df7b12defcadb21b31'

def check(data, label):
    if isinstance(data, bytes):
        try:
            text = data.decode('utf-8', errors='ignore')
        except:
            text = str(data)
    else:
        text = data
    
    if 'http' in text.lower() or 'safez' in text.lower() or 'google' in text.lower() or 'drive' in text.lower():
        print(f"!!! MATCH !!! [{label}]: {text}")
        return True
    return False

# Try many combinations
# 1. B64 -> ROT13
try:
    s = base64.b64decode(link_out_b64).decode('utf-8', errors='ignore')
    check(rot13(s), "B64 -> ROT13")
except: pass

# 2. ROT13 -> B64
try:
    check(base64.b64decode(rot13(link_out_b64)), "ROT13 -> B64")
except: pass

# 3. B64 -> ROT13 -> B64
try:
    s = base64.b64decode(link_out_b64).decode('utf-8', errors='ignore')
    r = rot13(s)
    # Remove any non-b64 chars for second decode
    r_clean = re.sub(r'[^a-zA-Z0-9+/=]', '', r)
    check(base64.b64decode(r_clean + '==='), "B64 -> ROT13 -> B64")
except: pass

# 4. XOR with api_key
try:
    check(xor_data(base64.b64decode(link_out_b64), api_key), "B64 -> XOR(key)")
except: pass

# 5. Reverse B64 -> XOR
try:
    check(xor_data(base64.b64decode(link_out_b64[::-1] + '==='), api_key), "ReverseB64 -> XOR(key)")
except: pass

# 6. B64 -> XOR(key) -> ROT13
try:
    x = xor_data(base64.b64decode(link_out_b64), api_key)
    check(rot13(x.decode('utf-8', errors='ignore')), "B64 -> XOR(key) -> ROT13")
except: pass

# 7. ROT13(link_out) -> B64 -> XOR(key)
try:
    r = rot13(link_out_b64)
    b = base64.b64decode(r + '===')
    check(xor_data(b, api_key), "ROT13 -> B64 -> XOR(key)")
except: pass

# 8. Try simple Caesar shifts (other than 13)
for i in range(1, 26):
    s = base64.b64decode(link_out_b64).decode('utf-8', errors='ignore')
    shifted = "".join(chr((ord(c) - 97 + i) % 26 + 97) if 'a' <= c <= 'z' else chr((ord(c) - 65 + i) % 26 + 65) if 'A' <= c <= 'Z' else c for c in s)
    if check(shifted, f"B64 -> Caesar({i})"): break

# 9. Is it a hex string encoded in B64?
try:
    b = base64.b64decode(link_out_b64)
    if check(b.hex(), "B64 -> Hex"): pass
except: pass

# 10. Doubly B64?
try:
    b1 = base64.b64decode(link_out_b64)
    b2 = base64.b64decode(b1)
    check(b2, "B64 -> B64")
except: pass

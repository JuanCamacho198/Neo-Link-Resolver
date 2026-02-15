import base64

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
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))

link_out_b64 = 'UTZBWWJQaVQ4eUlrRG5pTjdnMkhVaUZHWko2U0wxK0tNd3A4RmN1T1dvS1RJM1JuS3hjejlZQy9qOHhwYW40MEVGQWxWdFNSVmxOUTZJcHJudTQvellTci8xeXU1blhENlhMZC9Ed1oxTS96Z3FIT2VYcWJaalZFd1RUV1cySjN1eUZwbEVuSFpJM0VIYU0xT1M5NzY2b0dsZ2NDSk1DOS9pQVRMTzQ0YmlhZWFIb0ZMOVlLVjZSRVBaeHVxWENyN1ROcHhVVURSeU1PcW5COFgydFYvMkZnd20xU0Z4MGp5Qlc1QWFvNnJkTCt6UTB5TU9LcW0wQzBhMk10Y3EyZ0E5YkJJc0dxaW8rNkhIamZWWkdXNkE9PQ=='
api_key_hex = 'f866376a065f79df7b12defcadb21b31'

lo_bytes = base64.b64decode(link_out_b64)
key_bytes = bytes.fromhex(api_key_hex)

# Try XOR
res = xor_data(lo_bytes, key_bytes)
print(f"XOR result (bytes): {res[:50]}")
text = res.decode('utf-8', errors='ignore')
print(f"XOR result (text): {text[:100]}")

# Try ROT13 on XOR
print(f"XOR + ROT13: {rot13(text)[:100]}")

# Try if XOR result is B64
try:
    print(f"XOR -> B64 decode: {base64.b64decode(text.strip() + '==')[:50]}")
except: pass

# Try if XOR result is ROT13'd B64
try:
    rt = rot13(text)
    print(f"XOR -> ROT13 -> B64 decode: {base64.b64decode(rt.strip() + '==')[:50]}")
except: pass

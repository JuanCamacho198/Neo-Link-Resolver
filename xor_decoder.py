import base64

def xor_bytes(data, key):
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))

def find_target(text):
    for domain in ['safez', 'google', 'drive', 'bit.ly', 'tulink', 'domk5', 'http']:
        if domain in text.lower():
            return True
    return False

link_out_b64 = "UTZBWWJQaVQ4eUlrRG5pTjdnMkhVaUZHWko2U0wxK0tNd3A4RmN1T1dvS1RJM1JuS3hjejlZQy9qOHhwYW40MEVGQWxWdFNSVmxOUTZJcHJudTQvellTci8xeXU1blhENlhMZC9Ed1oxTS96Z3FIT2VYcWJaalZFd1RUV1cySjN1eUZwbEVuSFpJM0VIYU0xT1M5NzY2b0dsZ2NDSk1DOS9pQVRMTzQ0YmlhZWFIb0ZMOVlLVjZSRVBaeHVxWENyN1ROcHhVVURSeU1PcW5COFgydFYvMkZnd20xU0Z4MGp5Qlc1QWFvNnJkTCt6UTB5TU9LcW0wQzBhMk10Y3EyZ0E5YkJJc0dxaW8rNkhIamZWWkdXNkE9PQ=="
api_key = "f866376a065f79df7b12defcadb21b31"

data = base64.b64decode(link_out_b64)

# Try XOR with string key
decoded = xor_bytes(data, api_key.encode()).decode('utf-8', errors='ignore')
if find_target(decoded):
    print(f"FOUND XOR STRING: {decoded}")

# Try XOR with hex key
try:
    key_bytes = bytes.fromhex(api_key)
    decoded = xor_bytes(data, key_bytes).decode('utf-8', errors='ignore')
    if find_target(decoded):
        print(f"FOUND XOR HEX: {decoded}")
except: pass

# Try simple bitwise NOT or reverse
decoded = bytes(~b & 0xFF for b in data).decode('utf-8', errors='ignore')
if find_target(decoded):
    print(f"FOUND NOT: {decoded}")

# Try just B64 decode (without ROT13)
try:
    decoded = data.decode('utf-8', errors='ignore')
    print(f"RAW B64 (first 50 chars): {decoded[:50]}")
except: pass

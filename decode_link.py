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

link_out_b64 = 'UTZBWWJQaVQ4eUlrRG5pTjdnMkhVaUZHWko2U0wxK0tNd3A4RmN1T1dvS1RJM1JuS3hjejlZQy9qOHhwYW40MEVGQWxWdFNSVmxOUTZJcHJudTQvellTci8xeXU1blhENlhMZC9Ed1oxTS96Z3FIT2VYcWJaalZFd1RUV1cySjN1eUZwbEVuSFpJM0VIYU0xT1M5NzY2b0dsZ2NDSk1DOS9pQVRMTzQ0YmlhZWFIb0ZMOVlLVjZSRVBaeHVxWENyN1ROcHhVVURSeU1PcW5COFgydFYvMkZnd20xU0Z4MGp5Qlc1QWFvNnJkTCt6UTB5TU9LcW0wQzBhMk10Y3EyZ0E5YkJJc0dxaW8rNkhIamZWWkdXNkE9PQ=='

print(f"Original: {link_out_b64}")

# 1. B64 Decode
b64_1 = base64.b64decode(link_out_b64)
try:
    s1 = b64_1.decode('utf-8')
    print(f"B64_1 (string): {s1}")
    
    # 2. ROT13
    r1 = rot13(s1)
    print(f"ROT13 (r1): {r1}")
    
    # 3. B64 Decode again
    try:
        # LinkOut values in these sites sometimes need padding fix if they were cut
        padding_needed = (4 - len(r1) % 4) % 4
        r1_padded = r1 + ('=' * padding_needed)
        b64_2 = base64.b64decode(r1_padded)
        print(f"B64_2: {b64_2}")
        try:
            s2 = b64_2.decode('utf-8')
            print(f"B64_2 (string): {s2}")
        except:
            print("B64_2 is not a UTF-8 string")
    except Exception as e:
        print(f"B64_2 decode failed: {e}")
        
except Exception as e:
    print(f"B64_1 is not a UTF-8 string: {e}")
    # If not a string, maybe it's bytes ROT13? (not common but possible)
    pass

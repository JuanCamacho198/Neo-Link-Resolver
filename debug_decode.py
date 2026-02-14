import base64
import codecs

link_out = "UTZBWWJQaVQ4eUlrRG5pTjdnMkhVaUZHWko2U0wxK0tNd3A4RmN1T1dvS1RJM1JuS3hjejlZQy9qOHhwYW40MEVGQWxWdFNSVmxOUTZJcHJudTQvellTci8xeXU1blhENlhMZC9Ed1oxTS96Z3FIT2VYcWJaalZFd1RUV1cySjN1eUZwbEVuSFpJM0VIYU0xT1M5NzY2b0dsZ2NDSk1DOS9pQVRMTzQ0YmlhZWFIb0ZMOVlLVjZSRVBaeHVxWENyN1ROcHhVVURSeU1PcW5COFgydFYvMkZnd20xU0Z4MGp5Qlc1QWFvNnJkTCt6UTB5TU9LcW0wQzBhMk10Y3EyZ0E5YkJJc0dxaW8rNkhIamZWWkdXNkE9PQ=="

try:
    decoded = base64.b64decode(link_out)
    print(f"B64: {decoded}")
except Exception as e:
    print(f"B64 failed: {e}")

# Try ROT13 on the base64 string first
rot13_str = codecs.encode(link_out, 'rot_13')
try:
    decoded_rot = base64.b64decode(rot13_str)
    print(f"ROT13+B64: {decoded_rot}")
except: pass

# Try B64 then ROT13
try:
    decoded = base64.b64decode(link_out).decode('utf-8')
    print(f"B64+UTF8: {decoded}")
    print(f"B64+ROT13: {codecs.encode(decoded, 'rot_13')}")
except: pass

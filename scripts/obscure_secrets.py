def xor_bytes(data: str, key: bytes) -> bytes:
    encoded = data.encode()
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(encoded))


KEY = b'\x4f\x2a\x91\x3c'

client_id = ''
client_secret = ''

print(xor_bytes(client_id, KEY))  # b'\x2c\x59...'
print(xor_bytes(client_secret, KEY))  # b'\x6d\x4f...'

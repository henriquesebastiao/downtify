def xor_bytes(data: str, key: bytes) -> bytes:
    encoded = data.encode()
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(encoded))


KEY = b'\x4f\x2a\x91\x3c'

client_id = 'c3e98c954fbd469aa7023f8be6adcf70'
client_secret = '205557fcb24d4b328f436bb3a3bed130'

print(xor_bytes(client_id, KEY))  # b'\x2c\x59...'
print(xor_bytes(client_secret, KEY))  # b'\x6d\x4f...'

"""
Infosys ATP Match Centre — Decryption Utility
"""
import base64, hashlib, json
from Crypto.Cipher import AES
from datetime import datetime, timezone


def _to_base(n: int, base: int) -> str:
    if n == 0: return '0'
    digits = '0123456789abcdefghijklmnopqrstuvwxyz'
    result = []
    while n:
        result.append(digits[n % base])
        n //= base
    return ''.join(reversed(result))


def _derive_key_iv(last_modified_ms: int) -> tuple[bytes, bytes]:
    """
    Derives AES-128-CBC key and IV from the lastModified timestamp.
    Source: atptour.com main.js module 326, Fy.Y function.
    Key = "#" + 14-char derived string + "$"  (16 bytes)
    IV  = key.upper()
    """
    dt = datetime.fromtimestamp(last_modified_ms / 1000, tz=timezone.utc)
    a = dt.day
    day_str = str(a).zfill(2)
    r = int(day_str[::-1])
    n = dt.year
    s = int(str(n)[::-1])
    as_hex = int(str(last_modified_ms), 16)
    base36 = _to_base(as_hex, 36)
    second_part = _to_base((n + s) * (a + r), 24)
    i = base36 + second_part
    if len(i) < 14: i = i + '0' * (14 - len(i))
    elif len(i) > 14: i = i[:14]
    key_str = '#' + i + '$'
    return key_str.encode('utf-8'), key_str.upper().encode('utf-8')


def decrypt_infosys_response(response_obj: dict) -> dict:
    """
    Decrypt any Infosys ATP API response.
    All endpoints return { lastModified: <ms>, response: "<base64>", data: null }
    Pass the full parsed JSON object. Returns decrypted dict.

    Usage:
        raw = requests.get(url).json()
        data = decrypt_infosys_response(raw)
    """
    if not response_obj.get('lastModified') or not response_obj.get('response'):
        return response_obj.get('data') or response_obj

    key, iv = _derive_key_iv(response_obj['lastModified'])
    encrypted_b64 = response_obj['response'].strip()
    encrypted_b64 += '=' * (-len(encrypted_b64) % 4)
    ciphertext = base64.b64decode(encrypted_b64)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(ciphertext)
    pad_len = decrypted[-1]
    if 1 <= pad_len <= 16:
        decrypted = decrypted[:-pad_len]
    return json.loads(decrypted.decode('utf-8'))

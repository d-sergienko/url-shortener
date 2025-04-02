import base64
import hashlib


def create_short_link(original_url: str, timestamp: float, short_len: int):
    to_encode = f"{original_url}{timestamp}"

    b64_encoded_str = base64.urlsafe_b64encode(
        hashlib.sha256(to_encode.encode()).digest()
    ).decode()
    return b64_encoded_str[:short_len]  # changed 7-> 3    3-64   -> short_len
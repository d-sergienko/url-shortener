import base64
import hashlib

from sqlalchemy.orm import Session
from fastapi import Depends
from .db import ShortenedUrl, get_db_session


def create_short_link(original_url: str, timestamp: float, short_len: int):
    to_encode = f"{original_url}{timestamp}"

    b64_encoded_str = base64.urlsafe_b64encode(
        hashlib.sha256(to_encode.encode()).digest()
    ).decode()
    return b64_encoded_str[:short_len]  # changed 7-> 3    3-64   -> short_len

# check if short_link exists
def check_short_link(short_link: str, db: Session = Depends(get_db_session)):
    result = True
    check_obj = (
        db.query(ShortenedUrl)
        .filter_by(short_link=short_link)
        .order_by(ShortenedUrl.id.desc())
        .first()
    )
    if check_obj is None:
        result = False
    return result

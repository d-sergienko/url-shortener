from datetime import datetime, timezone

import logging
import time
import uuid

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse

from pydantic import BaseModel, HttpUrl
from typing import Annotated, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from .db import ShortenedUrl, get_db_session
from .service import create_short_link

# --------------------
# Logging Configuration
# --------------------
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG for very detailed logs
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("url-shortener")

app = FastAPI()

# --------------------
# Middleware for logging requests & responses
# --------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Generate a unique request ID
    request_id = str(uuid.uuid4())

    # Determine real client IP (handle proxy case)
    client_ip = request.headers.get("x-forwarded-for", request.client.host)
    # If multiple IPs in X-Forwarded-For, take the first one (real client)
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    # Log request details
    logger.debug(f"[{request_id}] Request start: {request.method} {request.url} from {client_ip}")
    logger.debug(f"[{request_id}] Headers: {dict(request.headers)}")
    body = await request.body()
    if body:
        logger.debug(f"[{request_id}] Body: {body.decode('utf-8', errors='ignore')}")

    # Process request
    try:
        response = await call_next(request)
    except Exception as e:
        logger.exception(f"[{request_id}] Unhandled error during request processing")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "request_id": request_id, "detail": str(e)}
        )

    # Calculate processing time
    process_time = (time.time() - start_time) * 1000
    logger.debug(f"[{request_id}] Request completed in {process_time:.2f}ms")
    logger.debug(f"[{request_id}] Response status: {response.status_code}")

    # Add request_id to response headers for tracing
    response.headers["X-Request-ID"] = request_id

    return response


class URL_To_Short(BaseModel):
    url: HttpUrl
    valid_until: Optional[datetime] = None
    short_len: Optional[int] = None

class URL_To_Short_Change(BaseModel):
    url: Optional[HttpUrl] = None
    valid_until: Optional[datetime] = None
    short_len: Optional[int] = None

short_links_cache = dict()


@app.post("/api/shorten")
def get_short_link(
    url_to_short: Annotated[URL_To_Short, Body(embed=False)],
    db: Session = Depends(get_db_session)
):

    timestamp = datetime.now().replace(tzinfo=timezone.utc).timestamp()
    url = url_to_short.url.unicode_string()

    short_link = None
    pre_line = None    
    pre_line = db.query(ShortenedUrl).filter_by(original_url=url).order_by(ShortenedUrl.id.desc()).first()
    if pre_line is not None:
        short_link = pre_line.short_link
        return {"short_link": short_link}

    short_len = 3
    if url_to_short.short_len:
        short_len = url_to_short.short_len
    if short_len > 64 or short_len < 3 or short_len is None:
        short_len = 3
    short_link = create_short_link(url, timestamp, short_len)
    while ( db.query(ShortenedUrl).filter_by(short_link=short_link).order_by(ShortenedUrl.id.desc()).first() ) is not None:
        short_link = create_short_link(url, timestamp)
    obj = ShortenedUrl(original_url=url, short_link=short_link, valid_until=url_to_short.valid_until)
    db.add(obj)
    db.commit()

    return {"short_link": short_link}

@app.get("/api/short_link")
def list_short_links(db: Session = Depends(get_db_session)):
    return db.query(ShortenedUrl).all()

@app.get("/api/short_link/{id}")
def get_short_link(id: int, db: Session = Depends(get_db_session)):
    link = db.get(ShortenedUrl, id)
    if not link:
        raise HTTPException(status_code=404, detail=f"Link id={id} not found")
    return link

@app.delete("/api/short_link/{id}")
def delete_short_link(id: int, db: Session = Depends(get_db_session)):
    link = db.get(ShortenedUrl, id)
    if not link:
        raise HTTPException(status_code=404, detail=f"Link id={id} not found")
    db.delete(link)
    db.commit()
    if link.short_link in short_links_cache.keys():
        short_links_cache.pop(link.short_link)
    return {"ok": True}

@app.put("/api/short_link/{id}")
def update_short_link(
    id: int,
    url_to_short: Annotated[URL_To_Short_Change, Body(embed=False)],
    db: Session = Depends(get_db_session)
):
    link: ShortenedUrl = db.get(ShortenedUrl, id)
    if not link:
        raise HTTPException(status_code=404, detail=f"Link id={id} not found")

    if (url_to_short.valid_until):
        link.valid_until = url_to_short.valid_until

    if (url_to_short.url):
        link.original_url = url_to_short.url.unicode_string()

    db.merge(link)
    db.commit()
    if link.short_link in short_links_cache.keys():
        short_links_cache.pop(link.short_link)
    return db.get(ShortenedUrl, id)


@app.get("/{short_link}")
def redirect(short_link: str, db: Session = Depends(get_db_session)):
    _now = datetime.now()
    if short_link in short_links_cache.keys() and short_links_cache[short_link].valid_until and short_links_cache[short_link].valid_until >= _now.astimezone():
        obj = short_links_cache[short_link]
    else:
        obj = (
            db.query(ShortenedUrl)
            .filter_by(short_link=short_link)
            .filter(or_(ShortenedUrl.valid_until >= _now, ShortenedUrl.valid_until == None))
            .order_by(ShortenedUrl.id.desc())
            .first()
        )
        if obj is None:
            raise HTTPException(
                status_code=404, detail="The link does not exist, could not redirect."
            )
        else:
            short_links_cache[short_link] = obj
    return RedirectResponse(url=obj.original_url)

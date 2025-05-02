from datetime import datetime, timezone

from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from pydantic import BaseModel, HttpUrl
from typing import Annotated, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from .db import ShortenedUrl, get_db_session
from .service import create_short_link

app = FastAPI()

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

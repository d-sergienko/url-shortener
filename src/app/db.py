import os

from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
engine = create_engine(DATABASE_URL, pool_size=30, max_overflow=20)
Base = declarative_base()
DBSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    session = DBSession()
    try:
        yield session
    except DBAPIError:
        session.rollback()
    finally:
        session.close()


class ShortenedUrl(Base):
    __tablename__ = "shortened_urls"

    id = Column(Integer, primary_key=True)
    original_url = Column(String(255))
    short_link = Column(String(3), unique=True, index=True)
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True)

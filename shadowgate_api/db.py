import os
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

def _url_with_params(url: str, **extra) -> str:
    p = urlparse(url)
    q = dict(parse_qsl(p.query))
    q.update({k: str(v) for k, v in extra.items() if v is not None})
    return urlunparse(p._replace(query=urlencode(q)))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    user = os.getenv("PGUSER")
    pwd = os.getenv("PGPASSWORD")
    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT", "5432")
    db = os.getenv("PGDATABASE", "railway")
    if user and pwd and host:
        DATABASE_URL = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
    else:
        raise RuntimeError("DATABASE_URL not set")

# --- FIXED: only require SSL for Railway's PUBLIC PROXY hosts ---
p = urlparse(DATABASE_URL)
host = (p.hostname or "").lower()

# Public proxy looks like *.proxy.rlwy.net on a high port
needs_ssl = host.endswith(".proxy.rlwy.net") or host == "proxy.rlwy.net"

DATABASE_URL = _url_with_params(
    DATABASE_URL,
    sslmode=("require" if needs_ssl else None),
    connect_timeout=5,
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

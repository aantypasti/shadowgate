# shadowgate_api/main.py
from pathlib import Path
import re

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from shadowgate_api.db import Base, engine
from shadowgate_api.routers import users, admin
from shadowgate_api.routers import loan_eligibility as elig
# Enable when those endpoints are ready:
# from shadowgate_api.routers import loans, trades

app = FastAPI(title="Shadowgate API")

MODELS_SQL = Path(__file__).with_name("models.sql")


def _split_sql_keep_dollar_blocks(sql: str) -> list[str]:
    """
    Split on semicolons that terminate statements, but DO NOT split inside
    Postgres $$...$$ dollar-quoted blocks.
    Also strips single-line comments starting with --.
    """
    # strip single-line comments (safe for DDL)
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)

    parts = []
    buf = []
    in_dollar = False
    i = 0
    while i < len(sql):
        # toggle on $$ boundaries
        if sql.startswith("$$", i):
            in_dollar = not in_dollar
            buf.append("$$")
            i += 2
            continue
        ch = sql[i]
        if ch == ";" and not in_dollar:
            s = "".join(buf).strip()
            if s:
                parts.append(s)
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


@app.on_event("startup")
def init_db_on_startup() -> None:
    """
    Apply models.sql (if present) as raw SQL statements.
    Otherwise create tables from SQLAlchemy metadata.
    """
    try:
        if MODELS_SQL.exists():
            raw = MODELS_SQL.read_text(encoding="utf-8")
            stmts = _split_sql_keep_dollar_blocks(raw)
            if not stmts:
                print("[db] models.sql is empty; skipping")
            else:
                with engine.begin() as conn:
                    for s in stmts:
                        # VERY IMPORTANT: pass a plain string, no params/compiled objects
                        conn.exec_driver_sql(s)
                print("[db] models.sql applied")
        else:
            # Fallback: create tables from models
            with engine.begin() as conn:
                Base.metadata.create_all(bind=conn)
            print("[db] metadata.create_all applied (models.sql not found)")
    except SQLAlchemyError as e:
        # Log and re-raise to fail fast in Railway
        print(f"[db] ERROR applying schema: {e}")
        raise


# --- Health check ---
@app.get("/")
def root():
    return {"message": "Shadowgate API running"}

# --- Routers ---
app.include_router(users.router)   # /api/users...
app.include_router(admin.router)   # /api/admin...
app.include_router(elig.router)    # /api/eligibility...
# app.include_router(loans.router)
# app.include_router(trades.router)

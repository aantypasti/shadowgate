# shadowgate_api/main.py
from fastapi import FastAPI

from shadowgate_api.db import Base, engine
from shadowgate_api.routers import users, admin
# from shadowgate_api.routers import trades, loans  # enable when ready

app = FastAPI(title="Shadowgate API")

# --- CORS: allow browser calls from any site (dev-friendly). Tighten later. ---
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost",
        "http://127.0.0.1",
        "*"  # loosened for now so you can test; tighten later if you want
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB init on boot ---
@app.on_event("startup")
def init_db() -> None:
    Base.metadata.create_all(bind=engine)

# --- Health check ---
@app.get("/")
def root():
    return {"message": "Shadowgate API running"}

# --- Routers ---
app.include_router(users.router)   # /api/...
app.include_router(admin.router)   # /api/admin/...
# app.include_router(trades.router)
# app.include_router(loans.router)

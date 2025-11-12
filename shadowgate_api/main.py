# shadowgate_api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shadowgate_api.db import Base, engine
from shadowgate_api.routers import users, admin
# from shadowgate_api.routers import trades, loans  # enable when ready

app = FastAPI(title="Shadowgate API")

# --- CORS: allow browser calls from any site (dev-friendly). Tighten later. ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # e.g. ["https://your-frontend.site"] once deployed
    allow_methods=["*"],      # GET, POST, OPTIONS, etc.
    allow_headers=["*"],      # Content-Type, Authorization, etc.
    allow_credentials=False,  # keep False when using "*"
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

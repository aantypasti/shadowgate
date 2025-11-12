# shadowgate_api/main.py
from fastapi import FastAPI

from shadowgate_api.db import Base, engine
from shadowgate_api.routers import users, admin
# from shadowgate_api.routers import trades, loans  # enable when ready
from shadowgate_api.routers import users, admin, loans, trades
from shadowgate_api.routers import loan_eligibility as elig


app = FastAPI(title="Shadowgate API")

# --- CORS: allow browser calls from any site (dev-friendly). Tighten later. ---
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # loosen for testing; tighten later to your domain(s)
    allow_credentials=False,    # you're not using cookies/sessions
    allow_methods=["*"],        # POST/GET/OPTIONS etc.
    allow_headers=["*"],        # Content-Type, Authorization, etc.
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
app.include_router(elig.router)
# app.include_router(trades.router)
# app.include_router(loans.router)

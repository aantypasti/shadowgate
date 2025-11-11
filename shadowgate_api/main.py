from fastapi import FastAPI
from shadowgate_api.db import Base, engine
from shadowgate_api.routers import users, admin
# from shadowgate_api.routers import trades, loans  # enable when implemented

app = FastAPI(title="Shadowgate API")

@app.on_event("startup")
def init_db():
    # Create tables once at startup
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "Shadowgate API running"}

app.include_router(users.router)
app.include_router(admin.router)
# app.include_router(trades.router)
# app.include_router(loans.router)

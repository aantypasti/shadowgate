from fastapi import APIRouter

router = APIRouter(prefix="/trades", tags=["Trades"])

@router.get("/")
def get_users():
    return {"message": "Trades endpoint working"}

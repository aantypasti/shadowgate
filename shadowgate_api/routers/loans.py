from fastapi import APIRouter

router = APIRouter(prefix="/loans", tags=["Loans"])

@router.get("/")
def get_users():
    return {"message": "Loans endpoint working"}

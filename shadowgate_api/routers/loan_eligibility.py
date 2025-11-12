# shadowgate_api/routers/loan_eligibility.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# ✅ use relative imports from inside the package
from ..db import get_db
from ..loan_eligibility_model import LoanEligibility

# Try root-level auth_simple first, then utils/auth as a fallback
try:
    from ..auth_simple import get_current_user        # shadowgate_api/auth_simple.py
except ImportError:
    try:
        from ..utils.auth import get_current_user     # shadowgate_api/utils/auth.py
    except ImportError:  # final fallback: we’ll raise a clear error at runtime
        get_current_user = None

router = APIRouter(prefix="/api/loan", tags=["loan"])


@router.get("/eligibility/{bases}")
def get_eligibility_for_bases(bases: int, db: Session = Depends(get_db)):
    rows = (
        db.query(LoanEligibility)
        .filter(LoanEligibility.bases == bases)
        .order_by(LoanEligibility.loan_type.asc(), LoanEligibility.max_amount.asc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No eligibility found for given bases")
    return [
        {
            "bases": r.bases,
            "type": r.loan_type,       # "Std" or "Shp"
            "max_amount": r.max_amount,
            "interest": r.interest,
        }
        for r in rows
    ]


# Only register /mine if we actually found the auth dependency
if get_current_user is not None:
    @router.get("/eligibility/mine")
    def get_my_eligibility(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
    ):
        bases = getattr(current_user, "bases", None)
        if bases is None:
            raise HTTPException(status_code=400, detail="User has no 'bases' field set")
        rows = (
            db.query(LoanEligibility)
            .filter(LoanEligibility.bases == bases)
            .order_by(LoanEligibility.loan_type.asc(), LoanEligibility.max_amount.asc())
            .all()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="No eligibility found for user")
        return [
            {
                "bases": r.bases,
                "type": r.loan_type,
                "max_amount": r.max_amount,
                "interest": r.interest,
            }
            for r in rows
        ]
else:
    @router.get("/eligibility/mine")
    def _missing_auth_dep():
        raise HTTPException(
            status_code=500,
            detail="Auth dependency not found. Move get_current_user to shadowgate_api/auth_simple.py "
                   "or shadowgate_api/utils/auth.py (and ensure __init__.py files exist).",
        )

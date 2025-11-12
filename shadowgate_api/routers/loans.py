# shadowgate_api/routers/loans.py
from datetime import datetime, timedelta, timezone
from math import ceil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth_simple import get_current_user  # adjust if you keep it elsewhere

router = APIRouter(prefix="/api/loans", tags=["loans"])


def _utcnow():
    return datetime.now(timezone.utc)


@router.get("/active")
def get_active_loan(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = text("""
        SELECT id, amount, end_date
        FROM loans
        WHERE user_id = :uid
          AND status = 'active'
          AND end_date > NOW()
        ORDER BY end_date DESC
        LIMIT 1
    """)
    row = db.execute(q, {"uid": current_user.id}).mappings().first()
    if row:
        return {"active": True, "loan_id": row["id"], "amount": int(row["amount"]), "ends_at": row["end_date"].isoformat()}
    return {"active": False}


@router.post("/apply")
def apply_loan(payload: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Expects JSON body:
    {
      "loan_type": "std" | "shp" | "refinance",
      "plan": "stable" | "interest-only",
      "amount": 123456,
      "repayment_rate": 0.10,            # decimal; 0 for interest-only
      "duration_weeks": 12,
      "purpose": "ship" | "standard" | "refinancing" | ...
    }
    """
    loan_type = (payload.get("loan_type") or "").lower()
    plan = (payload.get("plan") or "").lower()
    amount = int(payload.get("amount") or 0)
    repay = float(payload.get("repayment_rate") or 0.0)
    weeks = int(payload.get("duration_weeks") or 0)
    purpose = (payload.get("purpose") or "").lower()

    if loan_type not in ("std", "shp", "refinance"):
        raise HTTPException(status_code=400, detail="Invalid loan_type")
    if plan not in ("stable", "interest-only"):
        raise HTTPException(status_code=400, detail="Invalid plan")
    if amount <= 0 or weeks <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount/duration")
    if plan == "stable" and not (0 <= repay <= 1):
        raise HTTPException(status_code=400, detail="Invalid repayment_rate for stable plan")
    if plan == "interest-only":
        repay = 0.0

    # 1) Check for existing active loan
    active = db.execute(text("""
        SELECT id, amount, interest_rate
        FROM loans
        WHERE user_id = :uid AND status='active' AND end_date > NOW()
        ORDER BY end_date DESC
        LIMIT 1
    """), {"uid": current_user.id}).mappings().first()

    # 2) Refinancing special rule
    if active:
        if loan_type != "refinance" and purpose != "refinancing":
            raise HTTPException(status_code=400, detail="Active loan exists; only refinancing allowed.")
        max_ref = ceil(int(active["amount"]) / 2)
        if amount > max_ref:
            raise HTTPException(status_code=400, detail=f"Refinance cap is {max_ref}")
        interest_rate = float(active["interest_rate"])  # same rate as existing
    else:
        # 3) Normal eligibility path: fetch static tier by bases + type
        bases = getattr(current_user, "bases", None)
        row = db.execute(text("""
            SELECT max_amount, interest
            FROM loan_eligibility
            WHERE bases = :bases AND lower(loan_type) = :lt
            ORDER BY max_amount DESC
            LIMIT 1
        """), {"bases": bases, "lt": loan_type}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Eligibility tier not found.")
        if amount > int(row["max_amount"]):
            raise HTTPException(status_code=400, detail="Amount exceeds eligibility limit.")
        interest_rate = float(row["interest"])  # % per week

    # 4) Compute total interest (weekly)
    r = interest_rate / 100.0
    total_interest = 0.0
    principal = float(amount)
    if plan == "interest-only":
        total_interest = principal * r * weeks
    else:
        # stable: remaining principal decays by 'repay' proportion weekly
        for _ in range(weeks):
            total_interest += principal * r
            principal *= (1.0 - repay)

    total_interest_paid = int(round(total_interest))
    end_date = _utcnow() + timedelta(weeks=weeks)

    # 5) Insert loan (will fail with 23505 if unique index blocks a second active loan)
    ins = text("""
        INSERT INTO loans
        (user_id, loan_type, plan, amount, repayment_rate, interest_rate,
         total_interest_paid, duration_weeks, end_date, status)
        VALUES
        (:uid, :lt, :plan, :amount, :repay, :ir, :tip, :weeks, :endd, 'active')
        RETURNING id, date_granted, end_date
    """)
    try:
        ret = db.execute(ins, {
            "uid": current_user.id,
            "lt": loan_type,
            "plan": plan,
            "amount": amount,
            "repay": repay,
            "ir": interest_rate,
            "tip": total_interest_paid,
            "weeks": weeks,
            "endd": end_date,
        }).mappings().first()
        db.commit()
    except Exception as e:
        db.rollback()
        # surface unique-index violations more clearly
        msg = str(e)
        if "uniq_active_loan_per_user" in msg or "unique" in msg.lower():
            raise HTTPException(status_code=400, detail="You already have an active loan.")
        raise

    return {
        "loan_id": ret["id"],
        "interest_rate": interest_rate,
        "total_interest": total_interest_paid,
        "date_granted": ret["date_granted"].isoformat(),
        "end_date": ret["end_date"].isoformat(),
    }


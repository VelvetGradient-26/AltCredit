import uuid

from core import security
from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from services import user_service
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import models, schemas

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    """Check that the account exists and the password matches. No tokens are issued."""
    if body.role == "lender":
        account = db.scalar(
            select(models.Lender).where(models.Lender.username == body.username)
        )
        subject = str(account.lender_id) if account else ""
    else:
        account = db.scalar(
            select(models.User).where(
                or_(
                    models.User.user_id == body.username,
                    models.User.email == body.username.lower(),
                )
            )
        )
        subject = account.user_id if account else ""
    # same error for unknown account and wrong password
    if account is None or not security.verify_password(
        body.password, account.password_hash
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return {"role": body.role, "subject": subject}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: schemas.RegisterIn, db: Session = Depends(get_db)):
    """New-user portal: create a profile, then score the (thin) initial file."""
    email = body.email.lower()
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    count = db.scalar(select(func.count()).select_from(models.User)) or 0
    user_id = f"USR_{count + 1:03d}"
    while db.get(models.User, user_id):
        count += 1
        user_id = f"USR_{count + 1:03d}"
    user = models.User(
        user_id=user_id,
        applicant_id=str(uuid.uuid4()),
        full_name=body.full_name,
        email=email,
        password_hash=security.hash_password(body.password),
        age=body.age,
        city_tier=body.city_tier,
        employment_status=body.employment_status,
        education_level=body.education_level,
    )
    db.add(user)
    db.flush()
    demographics = body.model_dump(
        exclude={"full_name", "email", "password"}, exclude_none=True
    )
    result = user_service.record_scoring(db, user, demographics)
    return {
        "role": "user",
        "subject": user_id,
        "user_id": user_id,
        "credit_score": result["credit_score"],
        "risk_tier": result["risk_tier"],
        "missing_fields": result["missing_fields"],
    }


@router.post("/register-lender", status_code=status.HTTP_201_CREATED)
def register_lender(body: schemas.LenderRegisterIn, db: Session = Depends(get_db)):
    """Lender portal signup: create the institution with its lending policy."""
    if db.scalar(select(models.Lender).where(models.Lender.username == body.username)):
        raise HTTPException(status.HTTP_409_CONFLICT, "username already taken")
    if db.scalar(
        select(models.Lender).where(
            func.lower(models.Lender.company_name) == body.company_name.lower()
        )
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "company already registered")
    lender = models.Lender(
        company_name=body.company_name,
        username=body.username,
        password_hash=security.hash_password(body.password),
        min_credit_score_requirement=body.min_credit_score_requirement,
        max_pd_threshold=body.max_pd_threshold,
    )
    db.add(lender)
    db.commit()
    return {"role": "lender", "subject": str(lender.lender_id)}

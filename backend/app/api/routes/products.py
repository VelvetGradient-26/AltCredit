from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.dependencies import existing_user
from core.database import get_db
from services import bank_client, user_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def catalog():
    return list(user_service.product_catalog())


@router.get("/{user_id}/recommendations")
def recommendations(
    user: models.User = Depends(existing_user), db: Session = Depends(get_db)
):
    """Product matches; recomputed from the live score, so they update as the score changes."""
    result = user_service.score_user(db, user, with_details=False)
    return {"credit_score": result["credit_score"], **result["recommendations"]}


@router.post("/{user_id}/apply")
def apply(
    body: schemas.ApplyIn,
    user: models.User = Depends(existing_user),
    db: Session = Depends(get_db),
):
    """User clicks an offer: call the partner bank's API for the pre-approved product."""
    product = next(
        (
            p
            for p in user_service.product_catalog()
            if p["product_id"] == body.product_id
        ),
        None,
    )
    if product is None:
        raise HTTPException(404, "product not found")
    result = user_service.score_user(db, user, with_details=False)
    if result["credit_score"] < product["min_score"]:
        raise HTTPException(
            409,
            f"score {result['credit_score']:.0f} is below the {product['min_score']} required",
        )
    profile = user_service.current_profile(db, user)
    try:
        bank = bank_client.request_preapproval(
            {
                "applicant_id": user.applicant_id,
                "product_id": product["product_id"],
                "product_type": product["type"],
                "credit_score": int(result["credit_score"]),
                "min_score_required": product["min_score"],
                "monthly_income": float(profile.get("monthly_income") or 0),
            }
        )
    except bank_client.BankUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
    row = models.BankApplication(
        user_id=user.user_id,
        product_id=product["product_id"],
        status=bank["status"],
        bank_reference=bank.get("reference"),
        details=bank.get("details", {}),
    )
    db.add(row)
    db.commit()
    return {
        "product": product,
        "status": bank["status"],
        "bank_reference": bank.get("reference"),
        "details": bank.get("details", {}),
        "reason": bank.get("reason"),
    }


def _user_offers(db: Session, user_id: str):
    return db.execute(
        select(models.LoanOffer, models.Lender)
        .join(models.Lender)
        .join(models.AnonymousLead)
        .join(models.LoanApplication)
        .where(models.LoanApplication.user_id == user_id)
        .order_by(models.LoanOffer.offer_id.desc())
    ).all()


@router.get("/{user_id}/offers")
def offers(user: models.User = Depends(existing_user), db: Session = Depends(get_db)):
    """Offers pushed to this user by lenders."""
    return [
        {
            "offer_id": o.offer_id,
            "lender": lender.company_name,
            "offer_type": o.offer_type,
            "loan_amount": o.loan_amount,
            "interest_rate": o.interest_rate,
            "status": o.status,
            "created_at": o.created_at,
        }
        for o, lender in _user_offers(db, user.user_id)
    ]


@router.post("/{user_id}/offers/{offer_id}/respond")
def respond(
    offer_id: int,
    body: schemas.OfferResponseIn,
    user: models.User = Depends(existing_user),
    db: Session = Depends(get_db),
):
    """Accepting an offer is what de-anonymises the user to that lender."""
    match = next(
        (o for o, _ in _user_offers(db, user.user_id) if o.offer_id == offer_id), None
    )
    if match is None:
        raise HTTPException(404, "offer not found")
    if match.status != "OFFERED":
        raise HTTPException(409, f"offer already {match.status}")
    match.status = body.decision
    db.commit()
    return {"offer_id": offer_id, "status": match.status}

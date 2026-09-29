from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from services import user_service
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.dependencies import existing_lender

router = APIRouter(prefix="/lender/{lender_id}", tags=["lender"])


def _lead_view(lead: models.AnonymousLead) -> dict:
    """Anonymised candidate: no name, address, phone or user_id."""
    score = lead.credit_score
    tier = next((t["label"] for t in _tiers() if score >= t["min_score"]), "")
    return {
        "anon_lead_id": lead.anon_lead_id,
        "credit_score": score,
        "risk_tier": tier,
        "predicted_pd": lead.predicted_pd,
        "monthly_income": lead.monthly_income,
        "debt_to_income": lead.debt_to_income,
    }


def _tiers():
    from services.rule_engine import c as ml_config

    return ml_config.RISK_TIERS


@router.get("")
def me(lender: models.Lender = Depends(existing_lender)):
    return {
        "lender_id": lender.lender_id,
        "company_name": lender.company_name,
        "min_credit_score_requirement": lender.min_credit_score_requirement,
        "max_pd_threshold": lender.max_pd_threshold,
    }


@router.get("/candidates")
def search_candidates(
    min_score: float | None = Query(None, ge=0, le=1000),
    max_score: float | None = Query(None, ge=0, le=1000),
    max_pd: float | None = Query(None, ge=0, le=1),
    min_income: float | None = Query(None, ge=0),
    max_dti: float | None = Query(None, ge=0),
    q: str | None = Query(None, max_length=40),
    only_qualifying: bool = True,
    sort: str = Query("score_desc", pattern="^(score_desc|score_asc|income_desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    lender: models.Lender = Depends(existing_lender),
    db: Session = Depends(get_db),
):
    """Search/filter candidates. `only_qualifying` (default) also applies the lender's own score/PD policy."""
    L = models.AnonymousLead
    conds = [L.is_active.is_(True)]
    if only_qualifying:
        conds += [
            L.credit_score >= lender.min_credit_score_requirement,
            L.predicted_pd <= lender.max_pd_threshold,
        ]
    if q and q.strip():
        conds.append(L.anon_lead_id.ilike(f"%{q.strip()}%"))
    if min_score is not None:
        conds.append(L.credit_score >= min_score)
    if max_score is not None:
        conds.append(L.credit_score <= max_score)
    if max_pd is not None:
        conds.append(L.predicted_pd <= max_pd)
    if min_income is not None:
        conds.append(L.monthly_income >= min_income)
    if max_dti is not None:
        conds.append(L.debt_to_income <= max_dti)
    order = {
        "score_desc": L.credit_score.desc(),
        "score_asc": L.credit_score.asc(),
        "income_desc": L.monthly_income.desc(),
    }[sort]
    total = db.scalar(select(func.count()).select_from(L).where(*conds))
    rows = db.scalars(
        select(L)
        .where(*conds)
        .order_by(order, L.anon_lead_id)
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [_lead_view(r) for r in rows],
    }


@router.get("/candidates/{anon_lead_id}")
def candidate_detail(
    anon_lead_id: str,
    lender: models.Lender = Depends(existing_lender),
    db: Session = Depends(get_db),
):
    """Risk profile of one candidate - factor breakdown without identity."""
    lead = db.get(models.AnonymousLead, anon_lead_id)
    if lead is None or not lead.is_active:
        raise HTTPException(404, "candidate not found")
    result = user_service.score({**lead.application.profile})
    return {
        **_lead_view(lead),
        "pillar_breakdown": result["pillar_breakdown"],
        "subfactors": result["subfactor_breakdown"],
        "top_factors": result["explanation"]["top_contributors"][:3],
        "qualifies": lead.credit_score >= lender.min_credit_score_requirement
        and lead.predicted_pd <= lender.max_pd_threshold,
    }


@router.post("/offers", status_code=201)
def push_offers(
    body: schemas.OfferPushIn,
    lender: models.Lender = Depends(existing_lender),
    db: Session = Depends(get_db),
):
    """Push an offer to one or many candidates; only leads meeting the lender's policy get it."""
    created, skipped = [], []
    for lead_id in dict.fromkeys(body.anon_lead_ids):
        lead = db.get(models.AnonymousLead, lead_id)
        if lead is None or not lead.is_active:
            skipped.append({"anon_lead_id": lead_id, "reason": "not found"})
        elif (
            lead.credit_score < lender.min_credit_score_requirement
            or lead.predicted_pd > lender.max_pd_threshold
        ):
            skipped.append(
                {"anon_lead_id": lead_id, "reason": "does not meet lender policy"}
            )
        elif db.scalar(
            select(models.LoanOffer.offer_id).where(
                models.LoanOffer.lender_id == lender.lender_id,
                models.LoanOffer.anon_lead_id == lead_id,
                models.LoanOffer.status == "OFFERED",
            )
        ):
            skipped.append(
                {"anon_lead_id": lead_id, "reason": "open offer already exists"}
            )
        else:
            offer = models.LoanOffer(
                lender_id=lender.lender_id,
                anon_lead_id=lead_id,
                offer_type=body.offer_type,
                loan_amount=body.loan_amount,
                interest_rate=body.interest_rate,
            )
            db.add(offer)
            created.append(offer)
    db.commit()
    return {
        "created": [
            {"offer_id": o.offer_id, "anon_lead_id": o.anon_lead_id} for o in created
        ],
        "skipped": skipped,
    }


@router.get("/offers")
def list_offers(
    status: str | None = Query(None, pattern="^(OFFERED|ACCEPTED|DECLINED)$"),
    lender: models.Lender = Depends(existing_lender),
    db: Session = Depends(get_db),
):
    """The lender's offers. Identity is revealed only once the user has ACCEPTED."""
    q = (
        select(models.LoanOffer)
        .where(models.LoanOffer.lender_id == lender.lender_id)
        .order_by(models.LoanOffer.offer_id.desc())
    )
    if status:
        q = q.where(models.LoanOffer.status == status)
    out = []
    for o in db.scalars(q):
        row = {
            "offer_id": o.offer_id,
            "anon_lead_id": o.anon_lead_id,
            "offer_type": o.offer_type,
            "loan_amount": o.loan_amount,
            "interest_rate": o.interest_rate,
            "status": o.status,
            "created_at": o.created_at,
            "contact": None,
        }
        if o.status == "ACCEPTED":
            user = o.lead.application.user
            row["contact"] = {"full_name": user.full_name, "email": user.email}
        out.append(row)
    return out

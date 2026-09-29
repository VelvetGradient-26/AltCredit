from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.dependencies import existing_user
from core.database import get_db
from services import (
    data_parser,
    report_service,
    target_service,
    user_service,
    whatif_service,
)

router = APIRouter(prefix="/scoring", tags=["scoring"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@router.get("/{user_id}")
def get_score(
    user: models.User = Depends(existing_user), db: Session = Depends(get_db)
):
    """Score, tier, factor breakdown, explanation and product matches for one user."""
    return user_service.score_user(db, user)


@router.get("/{user_id}/history")
def history(user: models.User = Depends(existing_user), db: Session = Depends(get_db)):
    return user_service.score_history(db, user.user_id)


@router.put("/{user_id}/profile")
def update_profile(
    body: schemas.ProfileIn,
    user: models.User = Depends(existing_user),
    db: Session = Depends(get_db),
):
    """Create or update the profile (demographics + behaviour) and re-score."""
    merged = {
        **user_service.current_profile(db, user),
        **body.model_dump(exclude_none=True),
    }
    return user_service.record_scoring(db, user, merged)


@router.post("/{user_id}/transactions")
async def upload_transactions(
    file: UploadFile = File(...),
    user: models.User = Depends(existing_user),
    db: Session = Depends(get_db),
):
    """Upload a bank statement (CSV: date, amount, category, type[, status]); features are derived and re-scored."""
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "file too large (max 5 MB)")
    try:
        df = data_parser.parse_transactions(content)
    except Exception as exc:  # malformed csv / missing columns
        raise HTTPException(422, f"could not read transactions: {exc}") from exc
    profile = user_service.current_profile(db, user)
    derived = data_parser.features_from_transactions(
        df, profile.get("monthly_income") or None
    )
    result = user_service.record_scoring(db, user, {**profile, **derived})
    return {"transactions_read": len(df), "derived_features": derived, **result}


@router.post("/{user_id}/what-if")
def what_if(
    body: schemas.WhatIfIn,
    user: models.User = Depends(existing_user),
    db: Session = Depends(get_db),
):
    """Custom feature edits (absolute `changes` or relative `deltas`); the stored profile is never modified."""
    return _simulate(db, user, body)


def _simulate(db: Session, user: models.User, body: schemas.WhatIfIn) -> dict:
    if not (body.changes or body.deltas):
        raise HTTPException(422, "provide changes or deltas")
    unknown = [
        k for k in {**body.changes, **body.deltas} if k not in data_parser.REQUIRED_KEYS
    ]
    if unknown:
        raise HTTPException(422, f"unknown feature(s): {unknown}")
    return whatif_service.simulate(
        user_service.current_profile(db, user), body.changes, body.deltas
    )


@router.get("/{user_id}/target")
def target(
    product_id: str = Query(...),
    user: models.User = Depends(existing_user),
    db: Session = Depends(get_db),
):
    """Counterfactual: minimum feature changes needed to qualify for a product."""
    product = next(
        (p for p in user_service.product_catalog() if p["product_id"] == product_id),
        None,
    )
    if product is None:
        raise HTTPException(404, "product not found")
    plan = target_service.plan_for_target(
        user_service.current_profile(db, user), product["min_score"]
    )
    return {"product": product, **plan}


@router.get("/{user_id}/report.pdf")
def transparency_report(
    user: models.User = Depends(existing_user), db: Session = Depends(get_db)
):
    pdf = report_service.build_pdf(user_service.score_user(db, user), user.user_id)
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="transparency_{user.user_id}.pdf"'
        },
    )


@router.get("/{user_id}/export.json")
def export_profile(
    user: models.User = Depends(existing_user), db: Session = Depends(get_db)
):
    profile = user_service.current_profile(db, user)
    return report_service.profile_export(
        user_service.score(profile), profile, user.user_id
    )

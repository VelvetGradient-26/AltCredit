"""Scoring glue + persistence: applications, predictions, anonymous leads."""

from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from core import security
from services import data_parser
from services.explainability import build_explanation
from services.product_engine import recommend_products
from services.rule_engine import c as ml_config, engine


@lru_cache
def product_catalog() -> tuple[dict[str, Any], ...]:
    return tuple(data_parser.load_product_catalog())


def probability_of_default(score: float) -> float:
    """Inverse of the brief's Score = 1000 x (1 - PD); the data has no default label to train on."""
    return round(min(1.0, max(0.0, 1 - score / ml_config.MAX_CREDIT_SCORE)), 4)


def score(raw: dict[str, Any], with_details: bool = True) -> dict[str, Any]:
    """Run the rule engine on a (possibly incomplete) profile."""
    profile, missing = data_parser.normalise_profile(raw)
    ev = engine.evaluate_user(profile)
    value = ev["final_credit_score"]
    out = {
        "user_id": raw.get("user_id"),
        "applicant_id": raw.get("applicant_id"),
        "credit_score": value,
        "max_score": ml_config.MAX_CREDIT_SCORE,
        "risk_tier": ev["risk_tier"],
        "predicted_pd": probability_of_default(value),
        "score_capped": sum(ev["pillar_breakdown"].values())
        > ml_config.MAX_CREDIT_SCORE,
        "pillar_breakdown": ev["pillar_breakdown"],
        "subfactor_breakdown": ev["subfactor_breakdown"],
        "missing_fields": missing,
        "data_completeness": data_parser.data_completeness(missing),
        "recommendations": recommend_products(value, list(product_catalog())),
    }
    if with_details:
        out["explanation"] = build_explanation(ev)
    return out


def latest_application(db: Session, user_id: str) -> models.LoanApplication | None:
    return db.scalar(
        select(models.LoanApplication)
        .where(models.LoanApplication.user_id == user_id)
        .order_by(models.LoanApplication.application_id.desc())
        .limit(1)
    )


def current_profile(db: Session, user: models.User) -> dict[str, Any]:
    """Raw feature profile of the user's latest application (ids attached)."""
    app = latest_application(db, user.user_id)
    profile = dict(app.profile) if app else {}
    profile["user_id"], profile["applicant_id"] = user.user_id, user.applicant_id
    return profile


def score_user(
    db: Session, user: models.User, with_details: bool = True
) -> dict[str, Any]:
    return score(current_profile(db, user), with_details)


def _late_count(profile: dict[str, Any]) -> int:
    return sum(
        int(profile.get(k) or 0)
        for k in ("delinq_30plus", "delinq_60plus", "delinq_90plus")
    )


def record_scoring(
    db: Session,
    user: models.User,
    raw_profile: dict[str, Any],
    known_anon_ids: set[str] | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Score a profile, store the application + prediction, refresh the anonymous lead."""
    result = score(
        {**raw_profile, "user_id": user.user_id, "applicant_id": user.applicant_id}
    )
    profile, _ = data_parser.normalise_profile(raw_profile)
    app = models.LoanApplication(
        user_id=user.user_id,
        monthly_income=profile["monthly_income"],
        debt_to_income=profile["dti"],
        late_payments_count=_late_count(profile),
        profile={
            k: v for k, v in raw_profile.items() if k not in ("user_id", "applicant_id")
        },
    )
    db.add(app)
    db.flush()
    db.add(
        models.ScorePrediction(
            application_id=app.application_id,
            predicted_pd=result["predicted_pd"],
            credit_score=int(result["credit_score"]),
        )
    )

    lead = db.scalar(
        select(models.AnonymousLead)
        .join(models.LoanApplication)
        .where(models.LoanApplication.user_id == user.user_id)
    )
    if lead is None:
        existing = (
            known_anon_ids
            if known_anon_ids is not None
            else set(db.scalars(select(models.AnonymousLead.anon_lead_id)))
        )
        lead = models.AnonymousLead(
            anon_lead_id=security.new_anon_id(existing),
            application_id=app.application_id,
        )
        if known_anon_ids is not None:
            known_anon_ids.add(lead.anon_lead_id)
        db.add(lead)
    lead.application_id = app.application_id
    lead.credit_score, lead.predicted_pd = (
        int(result["credit_score"]),
        result["predicted_pd"],
    )
    lead.monthly_income, lead.debt_to_income = profile["monthly_income"], profile["dti"]
    lead.is_active = True
    if commit:
        db.commit()
    result["application_id"] = app.application_id
    return result


def score_history(db: Session, user_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        select(models.ScorePrediction, models.LoanApplication)
        .join(models.LoanApplication)
        .where(models.LoanApplication.user_id == user_id)
        .order_by(models.ScorePrediction.prediction_id)
    ).all()
    return [
        {
            "application_id": a.application_id,
            "credit_score": p.credit_score,
            "predicted_pd": p.predicted_pd,
            "evaluated_at": p.evaluated_at,
        }
        for p, a in rows
    ]

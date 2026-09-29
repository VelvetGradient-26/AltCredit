"""Idempotent seed: load the provided synthetic users and demo lenders."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from core import security
from core.config import settings
from services import data_parser, user_service

DEMO_LENDERS = [
    # company, username, min score, max PD
    ("Prime Bank", "primebank", 650, 0.35),
    ("MicroFin Capital", "microfin", 450, 0.55),
    ("NeoLend Fintech", "neolend", 550, 0.45),
]
PROFILE_SKIP = {"user_id", "applicant_id", "match_cost"}


def _demographics(row: dict) -> dict:
    return {"age": row.get("age"), "city_tier": row.get("city_tier"),
            "employment_status": row.get("employment_status"), "education_level": row.get("education_level")}


def _backfill_demographics(db: Session) -> None:
    """Older database files were seeded before these columns existed."""
    missing = db.scalars(select(models.User).where(models.User.age.is_(None))).all()
    if not missing:
        return
    rows = {r["user_id"]: r for r in data_parser.load_merged_users()}
    for user in missing:
        if user.user_id in rows:
            for k, v in _demographics(rows[user.user_id]).items():
                setattr(user, k, v)
    db.commit()


def seed(db: Session) -> None:
    password_hash = security.hash_password(
        settings.demo_password
    )  # hashed once, shared by demo accounts

    if not db.scalar(select(func.count()).select_from(models.Lender)):
        for name, username, min_score, max_pd in DEMO_LENDERS:
            db.add(
                models.Lender(
                    company_name=name,
                    username=username,
                    password_hash=password_hash,
                    min_credit_score_requirement=min_score,
                    max_pd_threshold=max_pd,
                )
            )
        db.commit()

    if db.scalar(select(func.count()).select_from(models.User)):
        _backfill_demographics(db)
        return
    users = data_parser.load_merged_users()
    anon_ids: set[str] = set()
    for row in users:
        user = models.User(
            user_id=row["user_id"],
            applicant_id=row.get("applicant_id"),
            full_name=f"Synthetic {row['user_id']}",
            email=f"{row['user_id'].lower()}@example.test",
            password_hash=password_hash,
            **_demographics(row),
        )
        db.add(user)
        db.flush()
        profile = {k: v for k, v in row.items() if k not in PROFILE_SKIP}
        user_service.record_scoring(
            db, user, profile, known_anon_ids=anon_ids, commit=False
        )
    db.commit()

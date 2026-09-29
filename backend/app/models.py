from datetime import datetime, timezone

from core.database import Base
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    applicant_id: Mapped[str | None] = mapped_column(String(64), index=True)
    full_name: Mapped[str] = mapped_column(
        String(120)
    )  # synthetic only, never real PII
    email: Mapped[str] = mapped_column(String(160), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(200))
    age: Mapped[int | None] = mapped_column(Integer)
    city_tier: Mapped[int | None] = mapped_column(Integer)
    employment_status: Mapped[str | None] = mapped_column(String(30))
    education_level: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    applications: Mapped[list["LoanApplication"]] = relationship(
        back_populates="user", order_by="LoanApplication.application_id"
    )


class LoanApplication(Base):
    __tablename__ = "loan_applications"
    application_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    monthly_income: Mapped[float] = mapped_column(Float)
    debt_to_income: Mapped[float] = mapped_column(Float)
    late_payments_count: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    profile: Mapped[dict] = mapped_column(JSON)  # feature snapshot that was scored
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    user: Mapped[User] = relationship(back_populates="applications")
    predictions: Mapped[list["ScorePrediction"]] = relationship(
        back_populates="application"
    )


class ScorePrediction(Base):
    __tablename__ = "score_predictions"
    prediction_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    application_id: Mapped[int] = mapped_column(
        ForeignKey("loan_applications.application_id"), index=True
    )
    predicted_pd: Mapped[float] = mapped_column(Float)
    credit_score: Mapped[int] = mapped_column(Integer)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    application: Mapped[LoanApplication] = relationship(back_populates="predictions")


class AnonymousLead(Base):
    __tablename__ = "anonymous_leads"
    anon_lead_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("loan_applications.application_id"), unique=True
    )
    credit_score: Mapped[int] = mapped_column(Integer, index=True)
    predicted_pd: Mapped[float] = mapped_column(Float)
    monthly_income: Mapped[float] = mapped_column(Float)
    debt_to_income: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    application: Mapped[LoanApplication] = relationship()


class Lender(Base):
    __tablename__ = "lenders"
    lender_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    company_name: Mapped[str] = mapped_column(String(120), unique=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(200))
    min_credit_score_requirement: Mapped[float] = mapped_column(Float)
    max_pd_threshold: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class LoanOffer(Base):
    __tablename__ = "loan_offers"
    offer_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lender_id: Mapped[int] = mapped_column(ForeignKey("lenders.lender_id"), index=True)
    anon_lead_id: Mapped[str] = mapped_column(
        ForeignKey("anonymous_leads.anon_lead_id"), index=True
    )
    offer_type: Mapped[str] = mapped_column(
        String(20), default="Loan"
    )  # Loan | Credit Card
    loan_amount: Mapped[float] = mapped_column(Float)
    interest_rate: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(
        String(10), default="OFFERED"
    )  # OFFERED, ACCEPTED, DECLINED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    lender: Mapped[Lender] = relationship()
    lead: Mapped[AnonymousLead] = relationship()


class BankApplication(Base):
    """Result of a user clicking a product (response from the bank's API)."""

    __tablename__ = "bank_applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    product_id: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    bank_reference: Mapped[str | None] = mapped_column(String(60))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

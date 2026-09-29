from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=1, max_length=200)
    role: Literal["user", "lender"] = "user"


class LenderRegisterIn(BaseModel):
    company_name: str = Field(min_length=2, max_length=120)
    username: str = Field(pattern=r"^[a-z0-9_]{3,40}$")
    password: str = Field(min_length=8, max_length=200)
    min_credit_score_requirement: float = Field(default=650, ge=0, le=1000)
    max_pd_threshold: float = Field(default=0.35, gt=0, le=1)


class ProfileIn(BaseModel):
    """Any subset of the engine's inputs; omitted fields keep their stored value."""

    model_config = ConfigDict(extra="forbid")
    age: int | None = Field(default=None, ge=18, le=100)
    education_level: str | None = None
    employment_status: Literal["Employed", "Self-Employed", "Student", "Unemployed"] | None = None
    city_tier: int | None = Field(default=None, ge=1, le=3)
    months_at_job: float | None = Field(default=None, ge=0)
    housing: Literal["owner", "rent", "none"] | None = None
    rent_on_time_months: float | None = Field(default=None, ge=0)
    digital_payment_rate: float | None = Field(default=None, ge=0, le=1)
    monthly_income: float | None = Field(default=None, ge=0)
    monthly_spend: float | None = Field(default=None, ge=0)
    essential_pct: float | None = Field(default=None, ge=0, le=1)
    cashflow_volatility: float | None = Field(default=None, ge=0)
    savings_days: float | None = Field(default=None, ge=0)
    on_time_rate: float | None = Field(default=None, ge=0, le=1)
    dti: float | None = Field(default=None, ge=0)
    credit_util: float | None = Field(default=None, ge=0)
    delinq_30plus: Literal[0, 1] | None = None
    delinq_60plus: Literal[0, 1] | None = None
    delinq_90plus: Literal[0, 1] | None = None
    positive_habits: int | None = Field(default=None, ge=0)
    risk_flags: int | None = Field(default=None, ge=0)


class WhatIfIn(BaseModel):
    changes: dict[
        str, float | str
    ] = {}  # absolute new values, e.g. {"months_at_job": 24}
    deltas: dict[str, float] = {}  # relative edits, e.g. {"dti": 0.1} for extra debt


class ApplyIn(BaseModel):
    product_id: str


class OfferResponseIn(BaseModel):
    decision: Literal["ACCEPTED", "DECLINED"]


class OfferPushIn(BaseModel):
    anon_lead_ids: list[str] = Field(min_length=1, max_length=500)
    loan_amount: float = Field(gt=0)
    interest_rate: float = Field(gt=0, le=100)
    offer_type: Literal["Loan", "Credit Card"] = "Loan"


class RegisterIn(ProfileIn):
    """New-user signup: account details plus the whole profile (every profile field is optional)."""
    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=160)
    password: str = Field(min_length=8, max_length=200)

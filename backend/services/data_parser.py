"""Ingestion: loaders for the three provided data types, plus normalisation.

The rule engine indexes ~18 keys directly and raises KeyError when one is
missing. `normalise_profile` guarantees every key exists (unknown numeric
values fall back to conservative defaults that earn 0 points) and reports
what was missing, so an applicant with, say, no utility history is scored
instead of crashing the pipeline.
"""

import io
import json
from typing import Any

import pandas as pd
from core.config import settings

# feature -> (default when unknown, lower bound, upper bound)
# Defaults are chosen to score 0 for the factor (conservative). Two exceptions,
# credit_util and the delinq_* flags, default to "no record": a thin-file
# applicant legitimately has no credit lines or delinquencies.
NUMERIC_FEATURES: dict[str, tuple[float, float, float | None]] = {
    "months_at_job": (0, 0, None),
    "rent_on_time_months": (0, 0, None),
    "digital_payment_rate": (0.0, 0, 1),
    "monthly_income": (0, 0, None),
    "essential_pct": (0.0, 0, 1),
    "cashflow_volatility": (1.0, 0, None),
    "savings_days": (0, 0, None),
    "on_time_rate": (0.0, 0, 1),
    "dti": (1.0, 0, None),
    "credit_util": (0.0, 0, None),
    "delinq_90plus": (0, 0, 1),
    "delinq_60plus": (0, 0, 1),
    "delinq_30plus": (0, 0, 1),
    "positive_habits": (0, 0, None),
    "risk_flags": (0, 0, None),
}
# monthly_spend defaults to monthly_income (ratio 100% -> 0 points)
TEXT_FEATURES = {"housing": "none", "education_level": "none"}
REQUIRED_KEYS = [*NUMERIC_FEATURES, "monthly_spend", *TEXT_FEATURES]
ID_KEYS = ("user_id", "applicant_id")
DEMOGRAPHIC_KEYS = (
    "age",
    "education_level",
    "employment_status",
    "monthly_income",
    "city_tier",
)

ESSENTIAL_CATEGORIES = {
    "food",
    "rent",
    "utility bill",
    "utility",
    "transport",
    "housing",
}
BILL_CATEGORIES = {"rent", "utility bill", "utility"}


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        f = float(value)
        return None if f != f else f  # NaN -> None
    except (TypeError, ValueError):
        return None


def normalise_profile(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return (engine-ready profile, missing_fields). Never raises on bad data."""
    profile: dict[str, Any] = dict(raw)
    missing: list[str] = []

    for key, (default, low, high) in NUMERIC_FEATURES.items():
        value = _num(raw.get(key))
        if value is None:
            missing.append(key)
            value = default
        value = max(low, value)
        if high is not None:
            value = min(high, value)
        profile[key] = value

    spend = _num(raw.get("monthly_spend"))
    if spend is None:
        missing.append("monthly_spend")
        spend = profile["monthly_income"]
    profile["monthly_spend"] = max(0.0, spend)

    for key, default in TEXT_FEATURES.items():
        value = raw.get(key)
        if value in (None, ""):
            # merged_data.json carries both 'education' (clean) and 'education_level'
            value = raw.get("education") if key == "education_level" else None
        if value in (None, ""):
            missing.append(key)
            value = default
        profile[key] = str(value)

    # ids are used for the engine's output envelope only
    profile.setdefault("user_id", None)
    profile.setdefault("applicant_id", None)
    return profile, missing


def data_completeness(missing: list[str]) -> float:
    return round(1 - len(missing) / len(REQUIRED_KEYS), 3)


# ---------------------------------------------------------------------------
# Provided datasets (machine_learning/data)
# ---------------------------------------------------------------------------
def _read_json(name: str) -> Any:
    path = settings.data_dir / name
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_merged_users() -> list[dict[str, Any]]:
    """Demographics + behavioural features, already joined per user."""
    with open(settings.merged_data_path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("merged_data.json must contain a list of users")
    return data


def load_demographics() -> list[dict[str, Any]]:
    return _read_json("demographic_data.json")


def load_product_catalog() -> list[dict[str, Any]]:
    data = _read_json("product_catalog.json")
    return data["products"] if isinstance(data, dict) else data


def load_transactions() -> pd.DataFrame:
    return parse_transactions(settings.data_dir / "transactional_data.csv")


# ---------------------------------------------------------------------------
# Transactions -> behavioural features (used for user uploads)
# ---------------------------------------------------------------------------
def parse_transactions(source: Any) -> pd.DataFrame:
    """Read a CSV (path / bytes / file-like) or a list of JSON records."""
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)
    if isinstance(source, list):
        df = pd.DataFrame(source)
    else:
        df = pd.read_csv(source)
    df.columns = [str(c).strip().lower() for c in df.columns]
    needed = {"date", "amount", "category", "type"}
    absent = needed - set(df.columns)
    if absent:
        raise ValueError(f"transactions missing columns: {sorted(absent)}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["date", "amount"])
    if df.empty:
        raise ValueError("no valid transaction rows found")
    df["category"] = df["category"].astype(str).str.strip().str.lower()
    df["type"] = df["type"].astype(str).str.strip().str.upper()
    if "status" not in df.columns:
        df["status"] = "Completed"
    df["status"] = df["status"].astype(str).str.strip().str.lower()
    df["month"] = df["date"].dt.to_period("M")
    return df


def features_from_transactions(
    df: pd.DataFrame, monthly_income: float | None = None
) -> dict[str, Any]:
    """Derive the spending / repayment features the rule engine consumes.

    Only fields that can be derived are returned; the caller merges them over
    the user's existing profile. Demographic/stability fields are not touched.
    """
    out: dict[str, Any] = {}
    months = max(df["month"].nunique(), 1)
    debits = df[df["type"] == "DEBIT"]
    credits = df[df["type"] == "CREDIT"]

    income = monthly_income or (
        credits["amount"].sum() / months if len(credits) else None
    )
    if income:
        out["monthly_income"] = round(float(income), 2)

    spend_rows = debits[debits["category"] != "savings"]
    if len(spend_rows):
        spend_total = spend_rows["amount"].sum()
        out["monthly_spend"] = round(float(spend_total / months), 2)
        if spend_total > 0:
            essential = spend_rows[spend_rows["category"].isin(ESSENTIAL_CATEGORIES)][
                "amount"
            ].sum()
            out["essential_pct"] = round(float(essential / spend_total), 3)

    bills = df[df["category"].isin(BILL_CATEGORIES)]
    if len(bills):
        out["on_time_rate"] = round(float((bills["status"] != "late").mean()), 3)
        util = bills[bills["category"].isin({"utility bill", "utility"})]
        if len(util):
            out["digital_payment_rate"] = round(
                float((util["status"] != "late").mean()), 3
            )
        rent = bills[(bills["category"] == "rent") & (bills["status"] != "late")]
        if len(rent):
            out["housing"] = "rent"
            out["rent_on_time_months"] = int(rent["month"].nunique())

    saved = debits[debits["category"] == "savings"]["amount"].sum()
    if out.get("monthly_spend"):
        out["savings_days"] = int(saved / (out["monthly_spend"] / 30))

    if months >= 2 and income:
        net = (
            credits.groupby("month")["amount"]
            .sum()
            .sub(debits.groupby("month")["amount"].sum(), fill_value=0)
            .reindex(sorted(df["month"].unique()), fill_value=0)
        )
        out["cashflow_volatility"] = round(float(net.std(ddof=0) / income), 3)

    late = int((df["status"] == "late").sum())
    out["delinq_30plus"] = 1 if late else 0  # no days-late column in the feed
    return out

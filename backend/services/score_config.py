# ==============================================================================
# ALTCREDIT SCORE FRAMEWORK - CONSTANTS & CONFIGURABLE THRESHOLDS
# ==============================================================================

# 1. LIFESTYLE PILLAR (MAX 350 PTS)
EMPLOYMENT_STABILITY_CONFIG = {
    "tiers": [
        {"min_months": 24, "points": 150},
        {"min_months": 12, "points": 100},
        {"min_months": 6, "points": 50},
        {"min_months": 0, "points": 0},
    ]
}

HOUSING_STATUS_CONFIG = {
    "owner_points": 80,
    "rent_ontime_min_months": 12,
    "rent_ontime_points": 60,
    "rent_short_points": 30,
    "none_points": 0,
}

DIGITAL_FOOTPRINT_CONFIG = {
    "tiers": [
        {"min_rate": 0.95, "points": 70},
        {"min_rate": 0.80, "points": 45},
        {"min_rate": 0.60, "points": 20},
        {"min_rate": 0.00, "points": 0},
    ]
}

EDUCATION_LEVEL_CONFIG = {
    "mapping": {
        "phd": 50,
        "master": 50,
        "bachelor": 40,
        "cert": 30,
        "diploma": 30,
        "high school": 20,
        "highschool": 20,
        "none": 0,
    }
}

# 2. SPENDING BEHAVIOR PILLAR (MAX 350 PTS)
SPEND_TO_INCOME_CONFIG = {
    "tiers": [
        {"max_ratio": 0.30, "points": 120},
        {"max_ratio": 0.50, "points": 80},
        {"max_ratio": 0.70, "points": 40},
        {"max_ratio": float("inf"), "points": 0},
    ]
}

EXPENSE_DIVERSITY_CONFIG = {
    "tiers": [
        {"min_essential_pct": 0.70, "points": 80},
        {"min_essential_pct": 0.55, "points": 45},
        {"min_essential_pct": 0.40, "points": 20},
        {"min_essential_pct": 0.00, "points": 0},
    ]
}

CASHFLOW_VOLATILITY_CONFIG = {
    "tiers": [
        {"max_volatility": 0.05, "points": 70},
        {"max_volatility": 0.10, "points": 40},
        {"max_volatility": 0.20, "points": 15},
        {"max_volatility": float("inf"), "points": 0},
    ]
}

SAVINGS_BUFFER_CONFIG = {
    "tiers": [
        {"min_days": 180, "points": 80},
        {"min_days": 90, "points": 50},
        {"min_days": 30, "points": 20},
        {"min_days": 0, "points": 0},
    ]
}

# 3. REPAYMENT DISCIPLINE PILLAR (MAX 570 RAW PTS)
ONTIME_PAYMENT_CONFIG = {
    "tiers": [
        {"min_rate": 0.98, "points": 200},
        {"min_rate": 0.95, "points": 150},
        {"min_rate": 0.90, "points": 100},
        {"min_rate": 0.80, "points": 50},
        {"min_rate": 0.00, "points": 0},
    ]
}

DEBT_TO_INCOME_CONFIG = {
    "tiers": [
        {"max_dti": 0.20, "points": 120},
        {"max_dti": 0.35, "points": 80},
        {"max_dti": 0.50, "points": 40},
        {"max_dti": float("inf"), "points": 0},
    ]
}

CREDIT_UTILIZATION_CONFIG = {
    "tiers": [
        {"max_util": 0.10, "points": 100},
        {"max_util": 0.30, "points": 70},
        {"max_util": 0.50, "points": 30},
        {"max_util": float("inf"), "points": 0},
    ]
}

DELINQUENCY_SEVERITY_CONFIG = {
    "clean_history_points": 150,
    "miss_30_points": 100,
    "miss_60_points": 50,
    "miss_90_plus_points": 0,
}

# 4. BONUS & PENALTY ADJUSTMENTS
BONUS_PENALTY_CONFIG = {
    "points_per_positive_habit": 20,
    "max_positive_bonus": 50,
    "penalty_per_risk_flag": 20,
    "max_risk_penalty": 50,
}

# SCORE CAP & TIERS
MIN_CREDIT_SCORE = 0
MAX_CREDIT_SCORE = 1000

RISK_TIERS = [
    {"min_score": 750, "label": "Prime / Low Risk"},
    {"min_score": 650, "label": "Near-Prime / Medium Risk"},
    {"min_score": 550, "label": "Sub-Prime / Fair"},
    {"min_score": 0, "label": "High Risk / Poor"},
]

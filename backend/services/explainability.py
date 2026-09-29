"""Factor analysis: turns the rule engine output into human-readable explanations."""

from typing import Any, Dict


# ============================================================
# HUMAN-READABLE FACTOR NAMES
# ============================================================

FACTOR_NAMES = {
    "1.1_employment_stability": "Employment Stability",
    "1.2_housing_status": "Housing Status",
    "1.3_digital_footprint": "Digital Payment Footprint",
    "1.4_education_level": "Education Level",
    "2.1_spend_to_income_ratio": "Spend-to-Income Ratio",
    "2.2_expense_diversity": "Expense Diversity",
    "2.3_cashflow_volatility": "Cash-flow Stability",
    "2.4_savings_emergency_fund": "Savings / Emergency Fund",
    "3.1_ontime_payment_rate": "On-time Payment Rate",
    "3.2_debt_to_income": "Debt-to-Income Ratio",
    "3.3_credit_utilization": "Credit Utilization",
    "3.4_delinquency_severity": "Recent Delinquency",
    "4.1_positive_habits": "Positive Financial Habits",
    "4.2_risk_flags": "Risk Flags",
}


# ============================================================
# PILLAR MAPPING
# ============================================================

PILLAR_NAMES = {
    "1.1_employment_stability": "Lifestyle",
    "1.2_housing_status": "Lifestyle",
    "1.3_digital_footprint": "Lifestyle",
    "1.4_education_level": "Lifestyle",
    "2.1_spend_to_income_ratio": "Spending Behaviour",
    "2.2_expense_diversity": "Spending Behaviour",
    "2.3_cashflow_volatility": "Spending Behaviour",
    "2.4_savings_emergency_fund": "Spending Behaviour",
    "3.1_ontime_payment_rate": "Repayment Discipline",
    "3.2_debt_to_income": "Repayment Discipline",
    "3.3_credit_utilization": "Repayment Discipline",
    "3.4_delinquency_severity": "Repayment Discipline",
    "4.1_positive_habits": "Adjustments",
    "4.2_risk_flags": "Adjustments",
}


# ============================================================
# CONTRIBUTION TYPE
# ============================================================


def get_contribution_type(score: float, max_score: float) -> str:

    if score < 0:
        return "negative"

    if score == 0:
        return "weak"

    if max_score > 0 and score >= max_score:
        return "strong"

    return "positive"


# ============================================================
# FACTOR EXPLANATION
# ============================================================


def generate_factor_explanation(
    factor_key: str, factor_data: Dict[str, Any]
) -> Dict[str, Any]:

    score = factor_data["score"]
    max_score = factor_data["max"]

    factor_name = FACTOR_NAMES.get(factor_key, factor_key)

    pillar = PILLAR_NAMES.get(factor_key, "Other")

    contribution_type = get_contribution_type(score, max_score)

    # --------------------------------------------------------
    # Generate human-readable explanation
    # --------------------------------------------------------

    if score > 0:
        explanation = (
            f"{factor_name} contributed "
            f"+{score} points. "
            f"Observed value: {factor_data['val']}."
        )

    elif score < 0:
        explanation = (
            f"{factor_name} reduced the score "
            f"by {abs(score)} points. "
            f"Observed value: {factor_data['val']}."
        )

    else:
        explanation = (
            f"{factor_name} contributed 0 points. Observed value: {factor_data['val']}."
        )

    return {
        "factor_key": factor_key,
        "factor": factor_name,
        "pillar": pillar,
        "score": score,
        "max_score": max_score,
        "contribution_type": contribution_type,
        "value": factor_data["val"],
        "explanation": explanation,
    }


# ============================================================
# BUILD COMPLETE EXPLANATION FOR ONE USER
# ============================================================


def build_explanation(evaluation: Dict[str, Any]) -> Dict[str, Any]:

    subfactors = evaluation["subfactor_breakdown"]

    factors = []

    for factor_key, factor_data in subfactors.items():
        factors.append(generate_factor_explanation(factor_key, factor_data))

    # --------------------------------------------------------
    # Sort strongest contributions first
    # --------------------------------------------------------

    positive_factors = sorted(
        [factor for factor in factors if factor["score"] > 0],
        key=lambda x: x["score"],
        reverse=True,
    )

    # --------------------------------------------------------
    # Negative factors
    # --------------------------------------------------------

    negative_factors = sorted(
        [factor for factor in factors if factor["score"] < 0], key=lambda x: x["score"]
    )

    # --------------------------------------------------------
    # Weak / zero factors
    # --------------------------------------------------------

    weak_factors = [factor for factor in factors if factor["score"] == 0]

    # --------------------------------------------------------
    # Top contributors
    # --------------------------------------------------------

    top_contributors = positive_factors[:5]

    # --------------------------------------------------------
    # Calculate contribution percentages
    # --------------------------------------------------------

    positive_total = sum(factor["score"] for factor in positive_factors)

    for factor in factors:
        if positive_total > 0 and factor["score"] > 0:
            factor["contribution_percentage"] = round(
                (factor["score"] / positive_total) * 100, 2
            )

        else:
            factor["contribution_percentage"] = 0

    # --------------------------------------------------------
    # Improvement suggestions
    # --------------------------------------------------------

    improvement_suggestions = []

    for factor in weak_factors:
        improvement_suggestions.append(
            {
                "factor": factor["factor"],
                "current_score": factor["score"],
                "potential_points": factor["max_score"],
                "suggestion": (
                    f"Improve {factor['factor']} "
                    f"to increase its contribution "
                    f"towards the credit score."
                ),
            }
        )

    return {
        "user_id": evaluation["user_id"],
        "applicant_id": evaluation["applicant_id"],
        "final_credit_score": evaluation["final_credit_score"],
        "risk_tier": evaluation["risk_tier"],
        "pillar_breakdown": evaluation["pillar_breakdown"],
        "factor_count": len(factors),
        "positive_factors": positive_factors,
        "negative_factors": negative_factors,
        "weak_factors": weak_factors,
        "top_contributors": top_contributors,
        "improvement_suggestions": improvement_suggestions,
        "all_factors": factors,
    }

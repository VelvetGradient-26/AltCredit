"""Counterfactual "Target Achievement": smallest feature changes that reach a product's score.

Candidate values are read from the tier tables in ml_config and every
candidate is scored by the real rule engine, so the plan can never drift from
the scoring rules.
"""

from typing import Any

from services import data_parser, user_service
from services.rule_engine import c as ml_config

# feature -> (config table, threshold key, higher_is_better, span used to size effort, advice)
LEVERS: dict[str, dict[str, Any]] = {
    "on_time_rate": dict(
        cfg="ONTIME_PAYMENT_CONFIG",
        key="min_rate",
        up=True,
        span=1.0,
        label="On-time Payment Rate",
        advice="Set up auto-pay for rent, utilities and loan instalments so no due date is missed.",
    ),
    "dti": dict(
        cfg="DEBT_TO_INCOME_CONFIG",
        key="max_dti",
        up=False,
        span=0.5,
        label="Debt-to-Income Ratio",
        advice="Pay down recurring debt or avoid new EMIs to lower obligations relative to income.",
    ),
    "credit_util": dict(
        cfg="CREDIT_UTILIZATION_CONFIG",
        key="max_util",
        up=False,
        span=1.0,
        label="Credit Utilization",
        advice="Keep card balances below the target share of your limit.",
    ),
    "cashflow_volatility": dict(
        cfg="CASHFLOW_VOLATILITY_CONFIG",
        key="max_volatility",
        up=False,
        span=0.3,
        label="Cash-flow Volatility",
        advice="Smooth month-to-month cash flow: automate savings and avoid one-off large spends.",
    ),
    "savings_days": dict(
        cfg="SAVINGS_BUFFER_CONFIG",
        key="min_days",
        up=True,
        span=180,
        label="Savings / Emergency Fund",
        advice="Build your emergency fund with a small automatic transfer each month.",
    ),
    "essential_pct": dict(
        cfg="EXPENSE_DIVERSITY_CONFIG",
        key="min_essential_pct",
        up=True,
        span=1.0,
        label="Expense Diversity",
        advice="Shift discretionary spend toward essentials (food, housing, utilities).",
    ),
    "digital_payment_rate": dict(
        cfg="DIGITAL_FOOTPRINT_CONFIG",
        key="min_rate",
        up=True,
        span=1.0,
        label="Digital Payment Footprint",
        advice="Pay mobile and internet bills on time every month.",
    ),
    "monthly_spend": dict(
        cfg="SPEND_TO_INCOME_CONFIG",
        key="max_ratio",
        up=False,
        span=1.0,
        label="Spend-to-Income Ratio",
        advice="Trim monthly spending relative to income.",
    ),
    "months_at_job": dict(
        cfg="EMPLOYMENT_STABILITY_CONFIG",
        key="min_months",
        up=True,
        span=36,
        label="Employment Stability",
        advice="Continuous employment / gig-platform earnings build this over time.",
    ),
}


def _candidates(feature: str, profile: dict[str, Any]) -> list[float]:
    lever = LEVERS[feature]
    values = []
    for tier in getattr(ml_config, lever["cfg"])["tiers"]:
        threshold = tier[lever["key"]]
        if threshold in (float("inf"), 0) and not lever["up"]:
            continue
        values.append(
            threshold * profile["monthly_income"]
            if feature == "monthly_spend"
            else threshold
        )
    return values


def _fmt(feature: str, value: float) -> str:
    if feature in {
        "on_time_rate",
        "dti",
        "credit_util",
        "cashflow_volatility",
        "essential_pct",
        "digital_payment_rate",
    }:
        return f"{value * 100:.0f}%"
    if feature == "monthly_spend":
        return f"{value:,.0f}/month"
    return f"{value:.0f} {'days' if feature == 'savings_days' else 'months'}"


def plan_for_target(
    raw: dict[str, Any], target_score: float, max_steps: int = 9
) -> dict[str, Any]:
    profile, _ = data_parser.normalise_profile(raw)
    current = user_service.score(raw, with_details=False)["credit_score"]
    steps: list[dict[str, Any]] = []
    score = current
    used: set[str] = set()

    while score < target_score and len(steps) < max_steps:
        options = []
        for feature, lever in LEVERS.items():
            if feature in used:
                continue
            old = profile[feature]
            for cand in _candidates(feature, profile):
                improves = cand > old if lever["up"] else cand < old
                if not improves:
                    continue
                trial = {**profile, feature: cand}
                gain = (
                    user_service.score(trial, with_details=False)["credit_score"]
                    - score
                )
                if gain <= 0:
                    continue
                effort = abs(cand - old) / (
                    lever["span"]
                    * (profile["monthly_income"] if feature == "monthly_spend" else 1)
                )
                options.append((effort, feature, old, cand, gain))
        if not options:
            break
        # a single change that closes the gap: take the cheapest, avoids overshooting;
        # otherwise the most points per unit of effort
        finishers = [o for o in options if o[4] >= target_score - score]
        effort, feature, old, cand, gain = (
            min(finishers)
            if finishers
            else max(options, key=lambda o: o[4] / max(o[0], 1e-6))
        )
        profile[feature] = cand
        used.add(feature)
        score += gain
        lever = LEVERS[feature]
        steps.append(
            {
                "feature": feature,
                "factor": lever["label"],
                "from": _fmt(feature, old),
                "to": _fmt(feature, cand),
                "points_gain": gain,
                "advice": lever["advice"],
                "action": f"{'Raise' if lever['up'] else 'Reduce'} {lever['label']} from {_fmt(feature, old)} to {_fmt(feature, cand)}.",
            }
        )

    achieved = user_service.score({**raw, **profile}, with_details=False)[
        "credit_score"
    ]
    reachable = achieved >= target_score
    summary = (
        "Already eligible - no change needed."
        if current >= target_score
        else f"Reach {target_score:.0f} with {len(steps)} change(s): "
        + "; ".join(s["action"] for s in steps)
        if reachable
        else f"Even with every supported improvement the projected score is {achieved:.0f}, short of {target_score:.0f}."
    )
    return {
        "current_score": current,
        "target_score": target_score,
        "points_needed": max(0, target_score - current),
        "projected_score": achieved,
        "reachable": reachable,
        "steps": steps,
        "summary": summary,
    }

"""What-if simulator: apply feature edits to a copy of the profile and re-score with the real engine."""

from typing import Any

from services import data_parser, user_service
from services.explainability import FACTOR_NAMES


def apply_changes(
    profile: dict[str, Any],
    changes: dict[str, Any] | None = None,
    deltas: dict[str, float] | None = None,
) -> dict[str, Any]:
    out = dict(profile)
    out.update(changes or {})
    for key, delta in (deltas or {}).items():
        out[key] = (data_parser._num(out.get(key)) or 0) + delta
    return out


def simulate(
    base_raw: dict[str, Any],
    changes: dict[str, Any] | None = None,
    deltas: dict[str, float] | None = None,
) -> dict[str, Any]:
    """`changes` set absolute values, `deltas` add to the current value. The stored profile is untouched."""
    base_profile, _ = data_parser.normalise_profile(base_raw)
    profile = apply_changes(base_profile, changes, deltas)

    before = user_service.score(base_raw, with_details=False)
    after = user_service.score({**base_raw, **profile}, with_details=False)

    factor_changes = []
    for key, old in before["subfactor_breakdown"].items():
        new = after["subfactor_breakdown"][key]
        if new["score"] != old["score"]:
            factor_changes.append(
                {
                    "factor": FACTOR_NAMES.get(key, key),
                    "key": key,
                    "before": old["score"],
                    "after": new["score"],
                    "delta": new["score"] - old["score"],
                    "value_before": old["val"],
                    "value_after": new["val"],
                }
            )

    def ids(result):
        return {p["product_id"] for p in result["recommendations"]["eligible_products"]}

    names = {p["product_id"]: p["product_name"] for p in user_service.product_catalog()}
    unlocked, revoked = (
        sorted(ids(after) - ids(before)),
        sorted(ids(before) - ids(after)),
    )
    capped = after["score_capped"] or before["score_capped"]
    return {
        "score_before": before["credit_score"],
        "score_after": after["credit_score"],
        "delta": after["credit_score"] - before["credit_score"],
        "tier_before": before["risk_tier"],
        "tier_after": after["risk_tier"],
        "score_capped": after["score_capped"],
        "cap_note": "Score is capped at 1000, so gains may look smaller than the point changes."
        if capped
        else None,
        "factor_changes": factor_changes,
        "products_unlocked": [
            {"product_id": i, "product_name": names[i]} for i in unlocked
        ],
        "products_revoked": [
            {"product_id": i, "product_name": names[i]} for i in revoked
        ],
    }

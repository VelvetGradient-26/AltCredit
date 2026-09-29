"""Product matching: which catalog products a score qualifies for."""

from typing import Any, Dict, List


# ============================================================
# PRODUCT HELPERS
# ============================================================


def get_product_id(product: Dict[str, Any]) -> str:

    return str(
        product.get("product_id") or product.get("id") or product.get("code") or ""
    )


def get_product_name(product: Dict[str, Any]) -> str:

    return str(
        product.get("product_name")
        or product.get("name")
        or product.get("title")
        or "Unknown Product"
    )


def get_min_score(product: Dict[str, Any]) -> float:

    return float(product.get("min_score") or product.get("minimum_score") or 0)


# ============================================================
# RECOMMEND PRODUCTS FOR ONE USER
# ============================================================


def recommend_products(score: float, products: List[Dict[str, Any]]) -> Dict[str, Any]:

    eligible = []
    ineligible = []

    for product in products:
        product_id = get_product_id(product)

        product_name = get_product_name(product)

        minimum_score = get_min_score(product)

        # ----------------------------------------------------
        # Eligible
        # ----------------------------------------------------

        if score >= minimum_score:
            eligible.append(
                {
                    "product_id": product_id,
                    "product_name": product_name,
                    "minimum_score": minimum_score,
                    "points_above_requirement": round(score - minimum_score, 2),
                    "eligibility": "eligible",
                    "product_details": product,
                }
            )

        # ----------------------------------------------------
        # Not eligible
        # ----------------------------------------------------

        else:
            ineligible.append(
                {
                    "product_id": product_id,
                    "product_name": product_name,
                    "minimum_score": minimum_score,
                    "points_needed": round(minimum_score - score, 2),
                    "eligibility": "not_eligible",
                    "product_details": product,
                }
            )

    # Highest score requirement first
    eligible.sort(key=lambda x: x["minimum_score"], reverse=True)

    # Closest product first
    ineligible.sort(key=lambda x: x["minimum_score"])

    highest_eligible = eligible[0] if eligible else None

    next_product = ineligible[0] if ineligible else None

    return {
        "current_score": score,
        "eligible_products": eligible,
        "ineligible_products": ineligible,
        "highest_eligible_product": highest_eligible,
        "next_product": next_product,
    }

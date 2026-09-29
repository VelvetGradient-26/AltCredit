"""Transparency Report (PDF) and credit-profile export (JSON)."""

import io
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def decision(result: dict[str, Any]) -> tuple[str, str]:
    eligible = result["recommendations"]["eligible_products"]
    if eligible:
        return (
            "ACCEPT",
            f"Eligible for {len(eligible)} product(s); best match: {eligible[0]['product_name']}.",
        )
    nxt = result["recommendations"]["next_product"]
    need = (
        f" {nxt['points_needed']:.0f} more points are needed for {nxt['product_name']}."
        if nxt
        else ""
    )
    return "REJECT", "Score is below the minimum requirement of every product." + need


def build_pdf(result: dict[str, Any], user_id: str) -> bytes:
    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="AltCredit Transparency Report",
    )
    verdict, why = decision(result)
    story: list[Any] = [
        Paragraph("AltCredit Transparency Report", styles["Title"]),
        Paragraph(
            f"Applicant: {user_id} &nbsp;|&nbsp; Generated: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
            styles["Normal"],
        ),
        Spacer(1, 6 * mm),
        Paragraph(f"Decision: <b>{verdict}</b>", styles["Heading2"]),
        Paragraph(why, styles["Normal"]),
        Spacer(1, 3 * mm),
        Paragraph(
            f"Credit score <b>{result['credit_score']:.0f} / {result['max_score']}</b> - {result['risk_tier']} "
            f"(estimated probability of default {result['predicted_pd']:.1%})",
            styles["Normal"],
        ),
        Spacer(1, 5 * mm),
        Paragraph("How the score was built", styles["Heading3"]),
    ]
    pillars = result["pillar_breakdown"]
    story.append(
        _table(
            [
                ["Pillar", "Points"],
                ["Lifestyle", pillars["lifestyle_score"]],
                ["Spending Behaviour", pillars["spending_behavior_score"]],
                ["Repayment Discipline", pillars["repayment_discipline_score"]],
                ["Bonus / penalty adjustments", pillars["net_adjustments"]],
            ]
        )
    )
    story += [Spacer(1, 5 * mm), Paragraph("Factor analysis", styles["Heading3"])]
    rows = [["Factor", "Observed", "Points", "Max"]]
    for f in result["explanation"]["all_factors"]:
        rows.append(
            [
                f["factor"],
                Paragraph(str(f["value"]), styles["BodyText"]),
                f["score"],
                f["max_score"],
            ]
        )
    story.append(_table(rows, widths=[60 * mm, 62 * mm, 22 * mm, 22 * mm]))
    story += [Spacer(1, 5 * mm), Paragraph("What would help most", styles["Heading3"])]
    for s in result["explanation"]["improvement_suggestions"][:5]:
        story.append(Paragraph(f"&bull; {s['suggestion']}", styles["Normal"]))
    if result["missing_fields"]:
        story += [
            Spacer(1, 4 * mm),
            Paragraph(
                f"Note: {len(result['missing_fields'])} input(s) were not available and scored conservatively: "
                f"{', '.join(result['missing_fields'])}.",
                styles["Italic"],
            ),
        ]
    story += [
        Spacer(1, 8 * mm),
        Paragraph(
            "Prototype using synthetic data. This is an assessment aid, not a legally binding credit decision.",
            styles["Italic"],
        ),
    ]
    doc.build(story)
    return buf.getvalue()


def _table(rows, widths=None):
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f3f6fa")],
                ),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return t


def profile_export(
    result: dict[str, Any], profile: dict[str, Any], user_id: str
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "credit_score": result["credit_score"],
        "risk_tier": result["risk_tier"],
        "predicted_pd": result["predicted_pd"],
        "pillar_breakdown": result["pillar_breakdown"],
        "subfactor_breakdown": result["subfactor_breakdown"],
        "eligible_products": [
            p["product_id"] for p in result["recommendations"]["eligible_products"]
        ],
        "missing_fields": result["missing_fields"],
        "input_profile": profile,
    }

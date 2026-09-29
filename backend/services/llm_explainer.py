"""Plain-language narration of a score, written by an LLM (gpt-oss:120b on Ollama Cloud).

The rule engine stays the single source of truth for every number. The model only
receives the finished breakdown plus the scoring methodology and is told to explain
it, never to re-score. If the LLM is unconfigured or fails, callers get a clear error
and the deterministic explanation from `explainability.build_explanation` still stands.
"""

import json
from pathlib import Path
from typing import Any

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", extra="ignore", env_prefix="OLLAMA_"
    )

    api_key: str = ""
    base_url: str = "https://ollama.com"
    model: str = "gpt-oss:120b"
    timeout_seconds: float = 90.0


class LLMUnavailable(RuntimeError):
    """Not configured, unreachable, or returned something unusable."""


METHODOLOGY = """\
AltCredit scores a person from 0 to 1000 with a transparent, rule-based framework
built for people with thin or no traditional credit files. Score = sum of pillar
points, capped at 1000. There is no black-box model; every point comes from a rule.

Pillar 1 - Lifestyle (max 350):
  1.1 Employment stability (max 150): >=24 months 150, >=12 100, >=6 50, else 0.
  1.2 Housing status (max 80): owner 80; renter with >=12 months on-time rent 60,
      shorter rent history 30; none 0.
  1.3 Digital payment footprint (max 70): share of digital payments >=95% 70,
      >=80% 45, >=60% 20, else 0.
  1.4 Education level (max 50): master/PhD 50, bachelor 40, certificate/diploma 30,
      high school 20, none 0.
Pillar 2 - Spending behaviour (max 350):
  2.1 Spend-to-income ratio (max 120): <=0.30 120, <=0.50 80, <=0.70 40, else 0.
  2.2 Expense diversity, essential-spend share (max 80): >=70% 80, >=55% 45, >=40% 20.
  2.3 Cash-flow volatility (max 70): <=0.05 70, <=0.10 40, <=0.20 15, else 0.
  2.4 Savings / emergency fund in days of expenses (max 80): >=180 80, >=90 50, >=30 20.
Pillar 3 - Repayment discipline (max 570 raw, capped by the 1000 total):
  3.1 On-time payment rate (max 200): >=98% 200, >=95% 150, >=90% 100, >=80% 50.
  3.2 Debt-to-income (max 120): <=0.20 120, <=0.35 80, <=0.50 40, else 0.
  3.3 Credit utilization (max 100): <=10% 100, <=30% 70, <=50% 30, else 0.
  3.4 Recent delinquency (max 150): clean 150, 30-day miss 100, 60-day 50, 90+ 0.
Pillar 4 - Adjustments: +20 per positive habit (max +50); -20 per risk flag (max -50).

Risk tiers: >=750 Prime / Low Risk; >=650 Near-Prime / Medium Risk;
>=550 Sub-Prime / Fair; below 550 High Risk / Poor.
Predicted probability of default = 1 - score/1000.
A factor "points" is what was earned; "max_points" is the most it could have earned.
"""

SYSTEM_PROMPT = f"""\
You are the explanation layer of AltCredit, an alternative credit scoring product.
Explain a person's credit score to that person in warm, plain, non-technical English.

Rules:
- Use ONLY the numbers in the provided data. Never invent, recompute or adjust a score,
  a threshold, or a factor value. If something is not in the data, do not mention it.
- Ground every claim in the methodology below (e.g. name the tier threshold the person
  is near and the points available at the next tier).
- Be honest about weaknesses without blaming or shaming. No jargon, no legal or
  financial-advice promises, no guarantees of approval.
- Address the reader as "you".

METHODOLOGY
{METHODOLOGY}
Respond with a single JSON object and nothing else, with exactly these keys:
  "summary": string, 2-3 sentences on the overall result and risk tier,
  "strengths": array of up to 3 strings (what helped most, with points),
  "weaknesses": array of up to 3 strings (what hurt or left points on the table),
  "next_steps": array of up to 3 strings (concrete, realistic actions, each tied to a
                factor and the points it could unlock)
"""


def _compact(scored: dict[str, Any]) -> dict[str, Any]:
    """Only what the model needs: totals, pillars, per-factor points, values."""
    expl = scored.get("explanation") or {}
    factors = [
        {
            "factor": f["factor"],
            "pillar": f["pillar"],
            "points": f["score"],
            "max_points": f["max_score"],
            "observed_value": f["value"],
        }
        for f in expl.get("all_factors", [])
    ]
    return {
        "credit_score": scored.get("credit_score"),
        "max_score": scored.get("max_score"),
        "risk_tier": scored.get("risk_tier"),
        "predicted_pd": scored.get("predicted_pd"),
        "score_capped": scored.get("score_capped"),
        "pillar_points": scored.get("pillar_breakdown"),
        "factors": factors,
        "missing_fields": scored.get("missing_fields"),
    }


def _parse(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):  # tolerate fenced output
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMUnavailable("model did not return valid JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("summary"), str):
        raise LLMUnavailable("model response missing 'summary'")
    return {
        "summary": data["summary"],
        **{
            k: [str(x) for x in data.get(k, [])][:3]
            for k in ("strengths", "weaknesses", "next_steps")
        },
    }


def explain_score(
    scored: dict[str, Any], client: httpx.Client | None = None
) -> dict[str, Any]:
    """Narrate the output of `user_service.score(...)`. Raises LLMUnavailable on any failure."""
    cfg = LLMSettings()
    if not cfg.api_key:
        raise LLMUnavailable("OLLAMA_API_KEY is not configured")
    payload = {
        "model": cfg.model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(_compact(scored))},
        ],
    }
    own = client is None
    client = client or httpx.Client(timeout=cfg.timeout_seconds)
    try:
        r = client.post(
            f"{cfg.base_url}/api/chat",
            json=payload,
            headers={"Authorization": f"Bearer {cfg.api_key}"},
        )
        r.raise_for_status()
        content = r.json()["message"]["content"]
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise LLMUnavailable(f"LLM request failed: {exc.__class__.__name__}") from exc
    finally:
        if own:
            client.close()
    return {"model": cfg.model, **_parse(content)}

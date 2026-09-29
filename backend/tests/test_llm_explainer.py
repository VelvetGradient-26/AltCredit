import json

import httpx
import pytest

from services import llm_explainer

SCORED = {
    "credit_score": 665,
    "max_score": 1000,
    "risk_tier": "Near-Prime / Medium Risk",
    "pillar_breakdown": {"lifestyle": 300},
    "explanation": {
        "all_factors": [
            {"factor": "Employment Stability", "pillar": "Lifestyle", "score": 150, "max_score": 150, "value": 30}
        ]
    },
}
GOOD = {"summary": "s", "strengths": ["a"], "weaknesses": ["b"], "next_steps": ["c", "d", "e", "f"]}


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_explain_score_sends_methodology_and_parses(monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "k")
    seen = {}

    def handler(req):
        seen["auth"] = req.headers["authorization"]
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"message": {"content": json.dumps(GOOD)}})

    out = llm_explainer.explain_score(SCORED, _client(handler))
    assert seen["auth"] == "Bearer k"
    assert seen["body"]["model"] == "gpt-oss:120b"
    assert "METHODOLOGY" in seen["body"]["messages"][0]["content"]
    assert json.loads(seen["body"]["messages"][1]["content"])["credit_score"] == 665
    assert out["summary"] == "s" and len(out["next_steps"]) == 3


def test_missing_key_raises(monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "")
    with pytest.raises(llm_explainer.LLMUnavailable):
        llm_explainer.explain_score(SCORED)


@pytest.mark.parametrize(
    "resp",
    [httpx.Response(500), httpx.Response(200, json={"message": {"content": "not json"}})],
)
def test_bad_upstream_raises(monkeypatch, resp):
    monkeypatch.setenv("OLLAMA_API_KEY", "k")
    with pytest.raises(llm_explainer.LLMUnavailable):
        llm_explainer.explain_score(SCORED, _client(lambda req: resp))

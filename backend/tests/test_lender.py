from core.config import settings

API = settings.api_prefix
FORBIDDEN_KEYS = {
    "user_id",
    "applicant_id",
    "full_name",
    "email",
    "name",
    "phone",
    "address",
}


def _walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, list):
        for i in obj:
            yield from _walk_keys(i)


def test_lender_search_is_anonymous_and_filtered(client, lender_id):
    L = f"{API}/lender/{lender_id('primebank')}"
    r = client.get(f"{L}/candidates", params={"min_score": 700, "limit": 20}).json()
    assert r["total"] > 0 and r["results"]
    assert all(
        c["credit_score"] >= 700 and c["anon_lead_id"].startswith("ANON-")
        for c in r["results"]
    )
    assert not FORBIDDEN_KEYS & set(_walk_keys(r))
    scores = [c["credit_score"] for c in r["results"]]
    assert scores == sorted(scores, reverse=True)
    # lender policy (score >= 650) is applied by default
    default = client.get(f"{L}/candidates", params={"limit": 200}).json()
    assert all(c["credit_score"] >= 650 for c in default["results"])
    wide = client.get(
        f"{L}/candidates", params={"only_qualifying": False, "max_score": 300}
    ).json()
    assert all(c["credit_score"] <= 300 for c in wide["results"])
    detail = client.get(f"{L}/candidates/{r['results'][0]['anon_lead_id']}").json()
    assert detail["pillar_breakdown"] and not FORBIDDEN_KEYS & set(_walk_keys(detail))
    assert client.get(f"{L}/candidates/ANON-NOPE").status_code == 404


def test_offer_lifecycle_reveals_identity_only_on_accept(client, lender_id):
    L = f"{API}/lender/{lender_id('primebank')}"
    # USR_002 (665) qualifies for Prime Bank (min 650)
    from app.main import app  # noqa: F401
    from core.database import SessionLocal
    from app import models
    from sqlalchemy import select

    with SessionLocal() as db:
        lead_id = db.scalar(
            select(models.AnonymousLead.anon_lead_id)
            .join(models.LoanApplication)
            .where(models.LoanApplication.user_id == "USR_002")
        )
        low = db.scalar(
            select(models.AnonymousLead.anon_lead_id).where(
                models.AnonymousLead.credit_score < 400
            )
        )
    body = {
        "anon_lead_ids": [lead_id, low, "ANON-NOPE"],
        "loan_amount": 50000,
        "interest_rate": 14.5,
    }
    r = client.post(f"{L}/offers", json=body)
    assert r.status_code == 201
    out = r.json()
    assert [c["anon_lead_id"] for c in out["created"]] == [lead_id]
    assert {s["reason"] for s in out["skipped"]} == {
        "does not meet lender policy",
        "not found",
    }
    # duplicate open offer is skipped
    again = client.post(f"{L}/offers", json={**body, "anon_lead_ids": [lead_id]}).json()
    assert (
        again["created"] == []
        and again["skipped"][0]["reason"] == "open offer already exists"
    )

    offers = client.get(f"{L}/offers").json()
    mine = next(o for o in offers if o["anon_lead_id"] == lead_id)
    assert mine["status"] == "OFFERED" and mine["contact"] is None

    user_offers = client.get(f"{API}/products/USR_002/offers").json()
    assert user_offers[0]["lender"] == "Prime Bank"
    assert client.get(f"{API}/dashboard/USR_002").json()["has_pending_offers"] is True
    assert (
        client.post(
            f"{API}/products/USR_002/offers/{mine['offer_id']}/respond",
            json={"decision": "ACCEPTED"},
        ).json()["status"]
        == "ACCEPTED"
    )
    assert (
        client.post(
            f"{API}/products/USR_002/offers/{mine['offer_id']}/respond",
            json={"decision": "DECLINED"},
        ).status_code
        == 409
    )
    revealed = next(
        o for o in client.get(f"{L}/offers").json() if o["offer_id"] == mine["offer_id"]
    )
    assert revealed["contact"]["email"] == "usr_002@example.test"
    # another user cannot answer this offer
    assert (
        client.post(
            f"{API}/products/USR_001/offers/{mine['offer_id']}/respond",
            json={"decision": "ACCEPTED"},
        ).status_code
        == 404
    )


def test_unknown_lender_and_bad_input(client, lender_id):
    assert client.get(f"{API}/lender/9999/candidates").status_code == 404
    L = f"{API}/lender/{lender_id('microfin')}"
    assert client.get(L).json()["company_name"] == "MicroFin Capital"
    assert (
        client.post(
            f"{L}/offers",
            json={"anon_lead_ids": [], "loan_amount": 1, "interest_rate": 1},
        ).status_code
        == 422
    )
    bad = client.post(
        f"{API}/auth/login",
        json={"username": "primebank", "password": "nope", "role": "lender"},
    )
    assert bad.status_code == 401

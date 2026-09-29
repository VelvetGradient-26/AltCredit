import io

from core.config import settings

API = settings.api_prefix


def test_end_to_end_profile_to_dashboard(client):
    """Integration: login -> score -> dashboard -> what-if -> report."""
    login = client.post(
        f"{API}/auth/login",
        json={"username": "USR_002", "password": settings.demo_password},
    )
    assert login.json() == {"role": "user", "subject": "USR_002"}

    body = client.get(f"{API}/scoring/USR_002").json()
    assert body["credit_score"] == 665 and body["risk_tier"].startswith("Near-Prime")
    assert (
        body["explanation"]["all_factors"]
        and body["recommendations"]["eligible_products"]
    )

    dash = client.get(f"{API}/dashboard/USR_002").json()
    assert dash["score"]["value"] == 665 and len(dash["score_bands"]) == 4
    assert (
        dash["credit_drivers"]["all_factors"]
        and dash["next_steps"]["next_product"]["product_id"] == "P_04"
    )

    wi = client.post(
        f"{API}/scoring/USR_002/what-if",
        json={"changes": {"delinq_30plus": 1, "on_time_rate": 0.5}},
    ).json()
    assert wi["delta"] < 0 and wi["products_revoked"]
    # simulation must not change the stored score
    assert client.get(f"{API}/scoring/USR_002").json()["credit_score"] == 665

    pdf = client.get(f"{API}/scoring/USR_002/report.pdf")
    assert (
        pdf.content.startswith(b"%PDF")
        and pdf.headers["content-type"] == "application/pdf"
    )
    export = client.get(f"{API}/scoring/USR_002/export.json").json()
    assert export["credit_score"] == 665 and "input_profile" in export


def test_what_if_custom_changes(client):
    up = client.post(
        f"{API}/scoring/USR_001/what-if", json={"changes": {"on_time_rate": 0.99}}
    ).json()
    assert up["delta"] > 0
    debt = client.post(
        f"{API}/scoring/USR_001/what-if", json={"deltas": {"dti": 0.3}}
    ).json()
    assert debt["delta"] <= 0
    assert client.post(f"{API}/scoring/USR_001/what-if", json={}).status_code == 422
    assert (
        client.post(
            f"{API}/scoring/USR_001/what-if", json={"changes": {"bogus": 1}}
        ).status_code
        == 422
    )
    # presets no longer exist
    assert client.get(f"{API}/scoring/what-if/scenarios").status_code == 404
    assert (
        "scenario"
        not in client.post(
            f"{API}/scoring/USR_001/what-if", json={"changes": {"dti": 0.1}}
        ).json()
    )


def test_target_achievement_counterfactual(client):
    r = client.get(
        f"{API}/scoring/USR_001/target", params={"product_id": "P_04"}
    ).json()
    assert (
        r["current_score"] == 635
        and r["reachable"]
        and r["projected_score"] >= 750
        and r["steps"]
    )
    done = client.get(
        f"{API}/scoring/USR_001/target", params={"product_id": "P_01"}
    ).json()
    assert done["steps"] == [] and "Already eligible" in done["summary"]
    assert (
        client.get(
            f"{API}/scoring/USR_001/target", params={"product_id": "P_99"}
        ).status_code
        == 404
    )


def test_login_checks_database(client):
    assert (
        client.post(
            f"{API}/auth/login", json={"username": "USR_001", "password": "wrong"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"{API}/auth/login",
            json={"username": "ghost", "password": settings.demo_password},
        ).status_code
        == 401
    )
    ok = client.post(
        f"{API}/auth/login",
        json={"username": "usr_001@example.test", "password": settings.demo_password},
    )
    assert ok.json()["subject"] == "USR_001"
    assert (
        client.post(
            f"{API}/auth/login",
            json={"username": "primebank", "password": settings.demo_password},
        ).status_code
        == 401
    )  # wrong role
    assert client.get(f"{API}/scoring/USR_9999").status_code == 404


def test_register_upload_and_thin_file_flow(client):
    reg = client.post(
        f"{API}/auth/register",
        json={
            "full_name": "Test Person",
            "email": "New.Person@example.test",
            "password": "longenough1",
            "age": 24,
            "education_level": "Bachelor",
            "employment_status": "Employed",
            "monthly_income": 4000,
        },
    )
    assert reg.status_code == 201, reg.text
    uid = reg.json()["user_id"]
    assert reg.json()["missing_fields"]  # thin file, still scored
    assert (
        client.post(
            f"{API}/auth/login", json={"username": uid, "password": "longenough1"}
        ).status_code
        == 200
    )
    dup = client.post(
        f"{API}/auth/register",
        json={
            "full_name": "X",
            "email": "new.person@example.test",
            "password": "longenough1",
        },
    )
    assert dup.status_code == 409

    before = client.get(f"{API}/scoring/{uid}").json()["credit_score"]
    csv = (
        "date,amount,category,type,status\n2024-01-01,4000,Salary,CREDIT,Completed\n2024-01-03,900,Rent,DEBIT,Completed\n"
        "2024-01-05,80,Utility Bill,DEBIT,Completed\n2024-01-09,300,Savings,DEBIT,Completed\n"
        "2024-02-01,4000,Salary,CREDIT,Completed\n2024-02-03,900,Rent,DEBIT,Completed\n"
        "2024-02-05,80,Utility Bill,DEBIT,Completed\n"
    ).encode()
    up = client.post(
        f"{API}/scoring/{uid}/transactions",
        files={"file": ("s.csv", io.BytesIO(csv), "text/csv")},
    )
    assert up.status_code == 200 and up.json()["transactions_read"] == 7
    assert up.json()["credit_score"] > before
    assert len(client.get(f"{API}/scoring/{uid}/history").json()) == 2

    bad = client.post(
        f"{API}/scoring/{uid}/transactions",
        files={"file": ("s.csv", io.BytesIO(b"a,b\n1,2"), "text/csv")},
    )
    assert bad.status_code == 422
    assert (
        client.put(
            f"{API}/scoring/{uid}/profile", json={"months_at_job": 30}
        ).status_code
        == 200
    )
    assert (
        client.put(f"{API}/scoring/{uid}/profile", json={"on_time_rate": 3}).status_code
        == 422
    )
    assert (
        client.put(f"{API}/scoring/{uid}/profile", json={"nonsense": 1}).status_code
        == 422
    )


def test_apply_via_bank_api(client, monkeypatch):
    # score 665: P_03 ok, P_04 (750) not
    ok = client.post(f"{API}/products/USR_002/apply", json={"product_id": "P_03"})
    assert (
        ok.status_code == 200
        and ok.json()["status"] == "APPROVED"
        and ok.json()["bank_reference"].startswith("BANK-")
    )
    assert (
        client.post(
            f"{API}/products/USR_002/apply", json={"product_id": "P_04"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{API}/products/USR_002/apply", json={"product_id": "zzz"}
        ).status_code
        == 404
    )

    # our side sends a key the bank does not accept -> surfaced as a 502, not a crash
    from types import SimpleNamespace
    from services import bank_client

    monkeypatch.setattr(
        bank_client,
        "settings",
        SimpleNamespace(
            bank_api_key="not-the-key",
            bank_api_url="http://bank",
            bank_timeout_seconds=1,
        ),
    )
    assert (
        client.post(
            f"{API}/products/USR_002/apply", json={"product_id": "P_03"}
        ).status_code
        == 502
    )

    def down():
        raise bank_client.httpx.ConnectError("refused")

    monkeypatch.setattr(bank_client, "get_client", down)
    assert (
        client.post(
            f"{API}/products/USR_002/apply", json={"product_id": "P_03"}
        ).status_code
        == 502
    )


def test_bank_rejects_missing_key():
    from fastapi.testclient import TestClient as TC
    from bank_mock.main import app as bank_app

    payload = {
        "applicant_id": "a",
        "product_id": "P_01",
        "product_type": "Loan",
        "credit_score": 700,
        "min_score_required": 500,
        "monthly_income": 1000,
    }
    c = TC(bank_app)
    assert c.post("/v1/preapproved-offers", json=payload).status_code == 401
    assert (
        c.post(
            "/v1/preapproved-offers", json=payload, headers={"X-API-Key": "bad"}
        ).status_code
        == 401
    )
    ok = c.post(
        "/v1/preapproved-offers",
        json=payload,
        headers={"X-API-Key": settings.bank_api_key},
    )
    assert ok.json()["status"] == "APPROVED"


def test_signup_stores_full_profile_in_sqlite(client):
    body = {
        "full_name": "Full Profile", "email": "full@example.test", "password": "longenough1",
        "age": 29, "city_tier": 2, "education_level": "Master's", "employment_status": "Self-Employed",
        "monthly_income": 6000, "months_at_job": 30, "housing": "rent", "rent_on_time_months": 14,
        "digital_payment_rate": 0.96, "monthly_spend": 2400, "essential_pct": 0.6, "savings_days": 100,
        "on_time_rate": 0.97, "cashflow_volatility": 0.08, "dti": 0.2, "credit_util": 0.15, "delinq_30plus": 0, "delinq_60plus": 0,
        "delinq_90plus": 0, "positive_habits": 2, "risk_flags": 0,
    }
    r = client.post(f"{API}/auth/register", json=body)
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["missing_fields"] == [] and out["risk_tier"]

    from sqlalchemy import select
    from app import models
    from core.database import SessionLocal
    with SessionLocal() as db:
        u = db.get(models.User, out["user_id"])
        assert (u.age, u.city_tier, u.employment_status, u.education_level) == (29, 2, "Self-Employed", "Master's")
        assert u.password_hash and "longenough1" not in u.password_hash
        app = db.scalar(select(models.LoanApplication).where(models.LoanApplication.user_id == u.user_id))
        assert app.profile["months_at_job"] == 30 and app.monthly_income == 6000
    assert client.get(f"{API}/scoring/{out['user_id']}").json()["credit_score"] == out["credit_score"]

    bad = {**body, "email": "other@example.test", "employment_status": "Astronaut"}
    assert client.post(f"{API}/auth/register", json=bad).status_code == 422
    assert client.post(f"{API}/auth/register", json={**body, "email": "x@example.test", "password": "short"}).status_code == 422

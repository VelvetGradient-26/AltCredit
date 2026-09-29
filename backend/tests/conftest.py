import os
import tempfile
from pathlib import Path

# Must be set before the app imports its settings.
_tmp = tempfile.mkdtemp(prefix="altcredit-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp) / 'test.db'}"
os.environ["PBKDF2_ITERATIONS"] = "1000"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from bank_mock.main import app as bank_app  # noqa: E402
from core.config import settings  # noqa: E402
from services import bank_client  # noqa: E402

API = settings.api_prefix


@pytest.fixture(scope="session")
def client():
    # the "bank" runs in-process; same X-API-Key contract as over the network
    bank_client.get_client = lambda: TestClient(bank_app, base_url="http://bank")
    with TestClient(app) as c:
        yield c


def _login(client, username, role="user"):
    r = client.post(
        f"{API}/auth/login",
        json={"username": username, "role": role, "password": settings.demo_password},
    )
    assert r.status_code == 200, r.text
    return r.json()["subject"]


@pytest.fixture(scope="session")
def lender_id(client):
    return lambda name="primebank": _login(client, name, "lender")

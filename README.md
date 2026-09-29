# AltCredit

**Alternative credit scoring for people with thin credit files.**

AltCredit scores users on 15 behavioural, lifestyle and repayment features instead of a
traditional bureau history — via a transparent, rule-based engine (no black-box ML) — and turns
that score into something actionable: a factor-by-factor explanation, a "what-if" simulator, a
counterfactual planner ("what do I need to change to qualify for product X"), live product
matching with a mock partner-bank hand-off, and an anonymised marketplace where lenders can find
and make offers to qualifying users without seeing their identity until they accept.

It's a full-stack prototype: a FastAPI + SQLite backend, a separate mock partner-bank API, and a
Vite + React frontend.

## Why

Traditional credit scoring locks out people with no/thin credit history even when their
underlying financial behaviour (steady employment, on-time rent, healthy spend-to-income ratio,
low volatility) is solid. AltCredit approximates a bureau-style score from that behavioural data
so those users become visible to lenders, while keeping every point of the score explainable —
each factor, its weight, and why it scored the way it did are always inspectable, unlike a
trained model.

## How it works

1. **Score** — 15 features (employment stability, housing, digital footprint, education,
   spend-to-income, expense diversity, cash-flow volatility, savings buffer, on-time payment rate,
   debt-to-income, credit utilisation, delinquency, positive habits, risk flags) feed a tiered
   rule engine across 3 pillars — **Lifestyle** (max 350), **Spending Behaviour** (max 350),
   **Repayment Discipline** (max 570) — plus ±50 adjustments, summed and capped to a **0–1000**
   score.
2. **Explain** — every factor is bucketed into positive / negative / weak contributors with a
   plain-language sentence, plus the top 5 drivers and improvement suggestions.
3. **Simulate & plan** — the what-if simulator re-scores a user with hypothetical changes; the
   target planner works backwards from a product's minimum score to the smallest set of feature
   changes that would qualify.
4. **Match & apply** — the score is checked against a small product catalog (Starter Card 350 /
   Micro-Loan Lite 550 / Standard Card 650 / Premium Loan 750); applying hands off to a separate
   mock bank API, which re-validates eligibility itself before approving.
5. **Lender marketplace** — lenders search and filter an **anonymised** pool of leads (score,
   tier, PD, income, DTI only — no name/email), and push offers in bulk. A user's identity is
   revealed to a lender only after that user explicitly accepts their offer.

Probability of default is derived directly from the score (`PD = 1 − score/1000`) rather than
trained, since the underlying dataset carries no default labels — see [Assumptions &
limitations](#assumptions--limitations).

## Project layout

```
AltCredit/
├── backend/               FastAPI API + SQLite (embedded, auto-seeded)
│   ├── app/               routes, ORM models, request schemas
│   ├── core/               settings, DB engine, password hashing
│   ├── services/           rule engine, scoring, what-if, target planner,
│   │                       explainability, product matching, PDF/JSON export
│   ├── bank_mock/          separate mock partner-bank FastAPI app (X-API-Key)
│   ├── data/               seed data (500 synthetic users)
│   ├── tests/               pytest suite (scoring, API, lender)
│   └── docs/BACKEND_GUIDE.md   full module-by-module walkthrough with diagrams
├── frontend/              Vite + React 19 UI (landing, sign-up, dashboard,
│   └── src/                 simulator, recommendations, lender portal)
├── machine_learning/      source data, cleaning notebook, product catalog
│   └── data/                 (still read by the backend at runtime)
└── Artifacts/             use-case doc, ER diagram, wireframes/design files
```

## Tech stack

| Layer | Stack |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2.0, SQLite, Pydantic v2, ReportLab (PDF), pytest |
| Frontend | React 19, React Router 7, Vite 8 |
| Mock partner bank | A second, independent FastAPI app, API-key protected |

## Getting started

Requires Python 3.13+ and Node 18+.

```bash
# 1. Backend API (terminal 1)
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env                                # optional — see below
.venv/bin/uvicorn app.main:app --port 8000           # -> http://localhost:8000/docs

# 2. Mock partner bank (terminal 2)
cd backend
.venv/bin/uvicorn bank_mock.main:app --port 8001

# 3. Frontend (terminal 3)
cd frontend
npm install
npm run dev                                          # -> http://localhost:5173 (proxies /api to :8000)
```

The first backend start creates `backend/altcredit.db` and auto-seeds 500 synthetic users (from
`backend/data/merged_data.json`) and 3 demo lenders. Seeding is idempotent — later restarts leave
existing data alone.

**Demo logins** (password is `DEMO_PASSWORD`, default `altcredit-demo`):
- Users: `USR_001` … `USR_500` (or use the "Demo preset" button on the sign-in page — `USR_002`)
- Lenders: `primebank`, `microfin`, `neolend`

### Run the tests

```bash
cd backend
.venv/bin/python -m pytest -q
```

Covers the rule engine against ground-truth CSVs for all 500 seeded users, end-to-end API flows
(scoring, what-if, target planning, registration, CSV upload, bank apply), and the lender
marketplace (anonymity guarantees, offer lifecycle, identity reveal on accept).

## API overview

All routes are under `/api/v1`. Full endpoint reference and request/response shapes:
[`backend/README.md`](backend/README.md) · [`backend/docs/BACKEND_GUIDE.md`](backend/docs/BACKEND_GUIDE.md).

| Area | What it covers |
|---|---|
| `auth` | Login (no tokens — prototype only), registration with full profile capture |
| `scoring` | Get score/explanation, update profile, upload transaction CSV, view history |
| `scoring/what-if` | Simulate profile changes without persisting them |
| `scoring/target` | Counterfactual plan to reach a product's minimum score |
| `scoring/report.pdf` / `export.json` | Transparency report / raw export |
| `dashboard` | One-call payload combining score, verdict, drivers, next steps, history |
| `products` | Catalog, live recommendations, apply (hands off to the mock bank), offers |
| `lender` | Anonymised candidate search & filtering, bulk offers, offer status |

There is **no authentication token** — every endpoint identifies the caller by the id in the URL
path. This is explicitly prototype-level; see the backend README for details.

## Assumptions & limitations

- **PD is derived, not trained.** `PD = 1 − score/1000`. The source dataset has no default label,
  so no ML default-probability model is trained (`scikit-learn`/`numpy` are pinned but unused).
- **Missing data** is filled with conservative (zero-point) defaults and reported back as
  `missing_fields`; a thin file with no recorded credit lines scores as "clean" rather than
  penalised, since absence isn't evidence of risk.
- **Score cap**: pillar maxima sum to ~1320 but the score is clamped to 1000, so a `score_capped`
  flag surfaces when the cap is masking further what-if gains.
- **No real authentication** — this is a prototype; anyone who knows a user/lender id can call
  that account's endpoints.
- Names, emails and other identity fields for the 500 seeded users are synthetic.

## Documentation

- [`backend/README.md`](backend/README.md) — backend run instructions, layout, API table, assumptions
- [`backend/docs/BACKEND_GUIDE.md`](backend/docs/BACKEND_GUIDE.md) — full module-by-module walkthrough with sequence/ER diagrams
- [`frontend/README.md`](frontend/README.md) — frontend run instructions and page map
- [`Artifacts/`](Artifacts) — original use-case document, ER diagram, and design wireframes

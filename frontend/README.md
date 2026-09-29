# ALTcredit frontend (Vite + React)

Implements the Stitch wireframes in `Artifacts/stitch_remix_of_altcredit_alternative_credit_scoring`:
a public landing page (`/`), sign in (`/login`), a four-step sign-up (`/signup`), dashboard, what-if simulator,
recommended products, and the lender portal.

```bash
# terminal 1 – API and bank (from backend/)
.venv/bin/uvicorn app.main:app --port 8000
.venv/bin/uvicorn bank_mock.main:app --port 8001
# terminal 2 – UI (from frontend/)
npm install && npm run dev      # http://localhost:5173, /api is proxied to :8000
```

Demo logins use the "Demo preset" button on the sign-in page (`USR_002`, or lender `primebank`).
Wireframe elements the backend has no data for (provider names, "% match", capital-pool allocation,
employment personas, tenure) are intentionally not shown rather than invented.

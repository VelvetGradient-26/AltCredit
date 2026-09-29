import { createContext, useContext, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { Brand } from '../components/Layout'
import { Icon, ScoreRing, fmt, tierMeta } from '../components/ui'
import './signup.css'

const STEPS = ['Account', 'About you', 'Work & home', 'Money habits']
const EDU = ['High School', 'Diploma', "Bachelor's", "Master's", 'PhD', 'Below high school']
const EMP = ['Employed', 'Self-Employed', 'Student', 'Unemployed']
const TIERS = [['1', 'Tier 1 (metro)'], ['2', 'Tier 2 (large city)'], ['3', 'Tier 3 (town / rural)']]
const VOLATILITY = [['0.04', 'Very steady (≤ 5% swing)'], ['0.08', 'Some variation (5–10%)'], ['0.15', 'Noticeable (10–20%)'], ['0.25', 'Large swings (> 20%)']]
const LATE = [['none', 'No missed payments'], ['30', 'Up to 30–59 days late'], ['60', 'Up to 60–89 days late'], ['90', '90+ days late']]

const INITIAL = {
  full_name: '', email: '', password: '', confirm: '',
  age: '', city_tier: '1', education_level: "Bachelor's", employment_status: 'Employed', monthly_income: '',
  months_at_job: '', housing: 'rent', rent_on_time_months: '', digital_pct: '',
  monthly_spend: '', essential_pct: '', savings_days: '', on_time_pct: '', volatility: '', dti_pct: '', util_pct: '',
  late: '', positive_habits: '', risk_flags: '',
}

const num = (v) => (v === '' ? undefined : Number(v))
const pct = (v) => (v === '' ? undefined : Number(v) / 100)

function buildPayload(f) {
  const late = f.late
  const payload = {
    full_name: f.full_name.trim(), email: f.email.trim(), password: f.password,
    age: num(f.age), city_tier: num(f.city_tier), education_level: f.education_level, employment_status: f.employment_status,
    monthly_income: num(f.monthly_income), months_at_job: num(f.months_at_job), housing: f.housing,
    rent_on_time_months: f.housing === 'rent' ? num(f.rent_on_time_months) : undefined,
    digital_payment_rate: pct(f.digital_pct), monthly_spend: num(f.monthly_spend), essential_pct: pct(f.essential_pct),
    savings_days: num(f.savings_days), on_time_rate: pct(f.on_time_pct), cashflow_volatility: num(f.volatility),
    dti: pct(f.dti_pct), credit_util: pct(f.util_pct), positive_habits: num(f.positive_habits), risk_flags: num(f.risk_flags),
  }
  if (late) {
    payload.delinq_30plus = late === 'none' ? 0 : 1
    payload.delinq_60plus = late === '60' || late === '90' ? 1 : 0
    payload.delinq_90plus = late === '90' ? 1 : 0
  }
  return Object.fromEntries(Object.entries(payload).filter(([, v]) => v !== undefined))
}

// Defined at module level (not inside Signup) so inputs keep focus while typing.
const FormCtx = createContext(null)

function Field({ k, label, hint, req, unit, ...p }) {
  const { f, set } = useContext(FormCtx)
  return (
    <label className="field"><span>{label}{req && <b className="req">*</b>}{hint && <small>{hint}</small>}</span>
      {unit ? <div className="unit" data-unit={unit}><input value={f[k]} onChange={set(k)} required={req} {...p} /></div>
        : <input value={f[k]} onChange={set(k)} required={req} {...p} />}</label>
  )
}

function Select({ k, label, options, req }) {
  const { f, set } = useContext(FormCtx)
  return (
    <label className="field"><span>{label}{req && <b className="req">*</b>}</span>
      <select value={f[k]} onChange={set(k)} required={req}>{!req && <option value="">Prefer not to say</option>}{options.map((o) => (Array.isArray(o) ? <option key={o[0]} value={o[0]}>{o[1]}</option> : <option key={o}>{o}</option>))}</select></label>
  )
}

export default function Signup() {
  const { register } = useAuth()
  const nav = useNavigate()
  const [step, setStep] = useState(0)
  const [f, setF] = useState(INITIAL)
  const [file, setFile] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const fileInput = useRef()
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const next = (e) => {
    e.preventDefault()
    setErr('')
    if (step === 0 && f.password !== f.confirm) return setErr('Passwords do not match.')
    if (step < STEPS.length - 1) return setStep(step + 1)
    submit()
  }

  const submit = async () => {
    setBusy(true); setErr('')
    try {
      const res = await register(buildPayload(f))
      let final = { ...res, upload: null }
      if (file) {
        try {
          const up = await api.uploadTransactions(res.user_id, file)
          final = { ...final, credit_score: up.credit_score, risk_tier: up.risk_tier, missing_fields: up.missing_fields, upload: { ok: true, n: up.transactions_read } }
        } catch (ex) { final.upload = { ok: false, msg: ex.message } }
      }
      setResult(final)
    } catch (ex) {
      setErr(ex.message)
      if (/email/i.test(ex.message) && !/email:/.test(ex.message)) setStep(0)
    } finally { setBusy(false) }
  }

  if (result) {
    const t = tierMeta(result.risk_tier)
    return (
      <div className="signup">
        <Brand />
        <div className="su-card su-done">
          <h1>You’re in, and scored!</h1>
          <ScoreRing value={result.credit_score} colour={t.colour} size={128}><Icon name="verified" /></ScoreRing>
          <div className="score-num">{fmt(result.credit_score)}<small className="muted">/ 1000</small></div>
          <span className={`chip ${t.chip}`}>{result.risk_tier}</span>
          <p className="su-hint">Your user ID is <b>{result.user_id}</b>. Your profile is saved and you can sign in with it or your email.</p>
          {result.upload?.ok && <div className="su-note"><Icon name="check_circle" />Statement parsed: {result.upload.n} transactions added to your score.</div>}
          {result.upload && !result.upload.ok && <div className="err">Your statement couldn’t be read ({result.upload.msg}). You can retry from the dashboard.</div>}
          {result.missing_fields.length > 0 && <div className="su-note"><Icon name="info" />{result.missing_fields.length} input(s) were left blank and scored conservatively. Add them or upload a statement from your dashboard to raise your score.</div>}
          <button className="btn btn-primary btn-lg" onClick={() => nav('/dashboard')}>Go to my dashboard <Icon name="arrow_forward" /></button>
        </div>
      </div>
    )
  }

  return (
    <div className="signup">
      <Link to="/" aria-label="ALTcredit home"><Brand /></Link>
      <FormCtx.Provider value={{ f, set }}>
      <form className="su-card" onSubmit={next}>
        <div className="stepper" aria-label={`Step ${step + 1} of ${STEPS.length}`}>
          {STEPS.map((s, i) => <div key={s} className={i < step ? 'done' : i === step ? 'now' : ''}><span>{s}</span></div>)}
        </div>

        {step === 0 && <>
          <div><h1>Create your ALTcredit profile</h1><p className="su-hint">No credit history needed. Use synthetic details only; this is a prototype.</p></div>
          <div className="su-grid">
            <div className="full"><Field k="full_name" label="Full name" req maxLength={120} autoComplete="name" /></div>
            <div className="full"><Field k="email" type="email" label="Email" req autoComplete="email" /></div>
            <Field k="password" type="password" label="Password" hint="min 8 characters" req minLength={8} autoComplete="new-password" />
            <Field k="confirm" type="password" label="Confirm password" req minLength={8} autoComplete="new-password" />
          </div></>}

        {step === 1 && <>
          <div><h1>About you</h1><p className="su-hint">Basic demographics that help place your finances in context.</p></div>
          <div className="su-grid">
            <Field k="age" type="number" min="18" max="100" label="Age" req />
            <Select k="city_tier" label="City tier" options={TIERS} req />
            <Select k="education_level" label="Highest education" options={EDU} req />
            <Select k="employment_status" label="Employment status" options={EMP} req />
            <div className="full"><Field k="monthly_income" type="number" min="0" step="any" label="Monthly income" hint="after tax, in your currency" req /></div>
          </div></>}

        {step === 2 && <>
          <div><h1>Work &amp; home stability</h1><p className="su-hint">Stability is one of the strongest signals when there’s no credit history.</p></div>
          <div className="su-grid">
            <Field k="months_at_job" type="number" min="0" label="Months at current job / gig platform" req />
            <Select k="housing" label="Housing" options={[['owner', 'I own my home'], ['rent', 'I rent'], ['none', 'No stable address']]} req />
            {f.housing === 'rent' && <Field k="rent_on_time_months" type="number" min="0" label="Months of on-time rent" />}
            <Field k="digital_pct" type="number" min="0" max="100" step="any" unit="%" label="Mobile / internet bills paid on time" hint="last 12 months" />
          </div></>}

        {step === 3 && <>
          <div><h1>Your money habits</h1><p className="su-hint">All optional. Anything you skip is scored conservatively and shown as missing. You can also upload a bank statement instead.</p></div>
          <div className="su-grid">
            <Field k="monthly_spend" type="number" min="0" step="any" label="Typical monthly spending" />
            <Field k="essential_pct" type="number" min="0" max="100" step="any" unit="%" label="Share spent on essentials" hint="food, housing, utilities" />
            <Field k="savings_days" type="number" min="0" label="Emergency savings" hint="days of expenses covered" />
            <Field k="on_time_pct" type="number" min="0" max="100" step="any" unit="%" label="All payments made on time" hint="last 12 months" />
            <Select k="volatility" label="Month-to-month cash-flow" options={VOLATILITY} />
            <Field k="dti_pct" type="number" min="0" step="any" unit="%" label="Debt payments vs income" />
            <Field k="util_pct" type="number" min="0" step="any" unit="%" label="Credit limit in use" hint="if you have any" />
            <Select k="late" label="Missed payments (24 months)" options={LATE} />
            <Field k="positive_habits" type="number" min="0" max="3" label="Positive habits" hint="0–3: savings app, charity…" />
            <Field k="risk_flags" type="number" min="0" max="5" label="Risk flags" hint="0–5: address changes, credit enquiries" />
            <div className="full">
              <div className="drop" style={{ padding: 18 }}>
                <Icon name="upload_file" /><strong>{file ? file.name : 'Optional: upload a bank statement (CSV)'}</strong>
                <small>Columns: date, amount, category, type, status</small>
                <div className="row"><button type="button" className="btn btn-tint btn-sm" onClick={() => fileInput.current.click()}>{file ? 'Change file' : 'Browse'}</button>
                  {file && <button type="button" className="btn btn-ghost btn-sm" onClick={() => setFile(null)}>Remove</button>}</div>
                <input ref={fileInput} type="file" accept=".csv" hidden onChange={(e) => setFile(e.target.files[0] || null)} />
              </div>
            </div>
          </div></>}

        {err && <div className="err" role="alert">{err}</div>}
        <div className="su-actions">
          {step > 0 ? <button type="button" className="btn btn-ghost" onClick={() => { setErr(''); setStep(step - 1) }}>Back</button> : <Link className="btn btn-ghost" to="/login">I have an account</Link>}
          <button className="btn btn-primary" disabled={busy}>{busy ? 'Creating…' : step < STEPS.length - 1 ? 'Continue' : 'Create profile & get scored'} <Icon name="arrow_forward" /></button>
        </div>
      </form>
      </FormCtx.Provider>
    </div>
  )
}

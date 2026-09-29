import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { Arc, ErrorBox, Icon, Spinner, fmt, tierMeta, useLoad } from '../components/ui'

const YN = [['0', 'No'], ['1', 'Yes']]
const EDU = ["High School", "Diploma", "Bachelor's", "Master's", "PhD", "None"]
// [key, label, hint, type, extra]
const SECTIONS = [
  { title: 'Lifestyle Pillar', tag: 'Pillar 1', icon: 'home', desc: 'Job stability, housing reliability, and educational attainment', fields: [
    ['months_at_job', 'Months at Job', 'Months', 'number', { min: 0 }],
    ['housing', 'Housing Status', 'Type', 'select', { options: [['owner', 'Own'], ['rent', 'Rent'], ['none', 'No stable address']] }],
    ['rent_on_time_months', 'On-Time Rent Months', 'Months', 'number', { min: 0 }],
    ['digital_payment_rate', 'Digital Bill Payment Rate', '0.00 – 1.00', 'number', { min: 0, max: 1, step: 0.01 }],
    ['education_level', 'Education Level', 'Highest qualification', 'edu'],
  ] },
  { title: 'Spending Behavior Pillar', tag: 'Pillar 2', icon: 'account_balance_wallet', desc: 'Income dynamics, cash-flow stability, essential expenditure, and reserves', fields: [
    ['monthly_income', 'Monthly Income', 'Currency', 'number', { min: 0 }],
    ['monthly_spend', 'Monthly Spend', 'Currency', 'number', { min: 0 }],
    ['essential_pct', 'Essential Spend Ratio', '0.00 – 1.00', 'number', { min: 0, max: 1, step: 0.01 }],
    ['cashflow_volatility', 'Cashflow Volatility', 'Ratio of income', 'number', { min: 0, step: 0.01 }],
    ['savings_days', 'Emergency Buffer (Savings Days)', 'Days', 'number', { min: 0 }],
  ] },
  { title: 'Repayment Discipline Pillar', tag: 'Pillar 3', icon: 'history', desc: 'Obligation performance, credit utilisation, and delinquency records', fields: [
    ['on_time_rate', 'Overall On-Time Rate', '0.00 – 1.00', 'number', { min: 0, max: 1, step: 0.01 }],
    ['dti', 'Debt-to-Income (DTI)', 'Ratio', 'number', { min: 0, step: 0.01 }],
    ['credit_util', 'Credit Utilization', 'Ratio', 'number', { min: 0, step: 0.01 }],
    ['delinq_30plus', '30+ Days Late (24 mo)', '30–59d', 'select', { options: YN }],
    ['delinq_60plus', '60+ Days Late (24 mo)', '60–89d', 'select', { options: YN }],
    ['delinq_90plus', '90+ Days Late (24 mo)', '90d+', 'select', { options: YN }],
  ] },
  { title: 'Bonus & Penalty Modifiers', tag: 'Modifiers', icon: 'tune', desc: 'Positive habit streaks and negative underwriting risk alerts', fields: [
    ['positive_habits', 'Positive Habit Markers', '0 – 3 count', 'number', { min: 0, max: 3 }],
    ['risk_flags', 'Negative Risk Flags', '0 – 5 count', 'number', { min: 0, max: 5 }],
  ] },
]
const ALL = SECTIONS.flatMap((s) => s.fields)


const toForm = (p) => Object.fromEntries(ALL.map(([k]) => [k, p[k] == null ? '' : String(p[k])]))

export default function Simulator() {
  const { userId } = useAuth()
  const { data, error, loading, reload } = useLoad(() => Promise.all([api.exportJson(userId), api.score(userId)]), [userId])
  const [form, setForm] = useState(null)
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => { if (data) setForm(toForm(data[0].input_profile)) }, [data])
  const base = useMemo(() => (data ? toForm(data[0].input_profile) : null), [data])

  if (loading && !data) return <Spinner />
  if (error) return <ErrorBox error={error} retry={reload} />
  if (!form) return null
  const [exp, score] = data
  const current = score.credit_score
  const projected = res ? res.score_after : current
  const delta = projected - current
  const t = tierMeta(res ? res.tier_after : score.risk_tier)

  const run = async (body) => {
    setBusy(true); setErr('')
    try { setRes(await api.whatIf(userId, body)) } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const recalc = () => {
    const changes = {}
    for (const [k] of ALL) {
      if (form[k] === '' || form[k] === base[k]) continue
      const v = k === 'housing' || k === 'education_level' ? form[k] : Number(form[k])
      if (typeof v === 'number' && Number.isNaN(v)) return setErr(`"${k}" must be a number`)
      changes[k] = v
    }
    if (!Object.keys(changes).length) return setErr('Change at least one value first.')
    run({ changes })
  }
  const reset = () => { setForm(base); setRes(null); setErr('') }
  const setK = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const eduOptions = form.education_level && !EDU.includes(form.education_level) ? [form.education_level, ...EDU] : EDU

  return (
    <>
      <div>
        <Link to="/dashboard" className="link"><Icon name="arrow_back" /> Back to Dashboard</Link>
        <div className="row wrap" style={{ marginTop: 8 }}><h1>What-If Credit Simulator</h1><span className="chip chip-blue">REAL-TIME ENGINE</span></div>
        <p className="muted">Change the inputs below to see the impact on your ALTcredit score. Your stored profile is never changed.</p>
      </div>

      <section className="sim-hero" aria-live="polite">
        <div>
          <div className="label" style={{ color: '#94a3b8' }}>Current score</div>
          <div className="row" style={{ gap: 16 }}><span className="big">{fmt(current)}</span>
            {res && <span className={delta >= 0 ? 'pill-up' : 'pill-down'}>{delta >= 0 ? '+' : ''}{delta} pts</span>}</div>
          <p style={{ marginTop: 12, color: '#94a3b8' }}>{score.risk_tier}</p>
        </div>
        <div className="center">
          <div className="label" style={{ color: '#4edea3' }}>● Projected score</div>
          <Arc value={projected} colour={t.colour} />
          <div style={{ position: 'relative' }}><span className="big" style={{ fontSize: 52 }}>{fmt(projected)}</span><small style={{ color: '#94a3b8' }}> / 1000</small></div>
          <div className="chip" style={{ marginTop: 10, background: 'rgba(255,255,255,.1)', color: '#fff' }}>Tier: {res ? res.tier_after : score.risk_tier}</div>
        </div>
        <div className="panel">
          <div className="label" style={{ color: '#94a3b8', marginBottom: 6 }}>Factor contributions</div>
          {!res && <small style={{ color: '#94a3b8' }}>Recalculate to see which factors move.</small>}
          {res?.factor_changes.map((c) => (
            <div className="row between" key={c.key}><span>{c.factor}<br /><small style={{ color: '#94a3b8' }}>{c.value_before} → {c.value_after}</small></span>
              <span className={c.delta >= 0 ? 'pill-up' : 'pill-down'}>{c.delta >= 0 ? '+' : ''}{c.delta}</span></div>))}
          {res && !res.factor_changes.length && <small style={{ color: '#94a3b8' }}>No factor crossed a scoring tier.</small>}
        </div>
      </section>

      {res && (res.cap_note || res.products_unlocked.length > 0 || res.products_revoked.length > 0) && (
        <section className="card">
          {res.products_unlocked.map((p) => <div key={p.product_id} className="row" style={{ color: 'var(--emerald-d)' }}><Icon name="lock_open" /> Unlocks {p.product_name}</div>)}
          {res.products_revoked.map((p) => <div key={p.product_id} className="row" style={{ color: '#b91c1c' }}><Icon name="lock" /> Would revoke {p.product_name}</div>)}
          {res.cap_note && <div className="muted"><Icon name="info" /> {res.cap_note}</div>}
        </section>
      )}

      <div className="row between wrap"><h2><Icon name="tune" /> Simulate Scenarios</h2><button className="btn btn-ghost btn-sm" onClick={reset}><Icon name="restart_alt" /> Reset All</button></div>
      <section className="card">
        <div className="row between"><div className="row"><span className="section-icon"><Icon name="badge" /></span><div><h3>Session Metadata</h3><small>Anonymised applicant identifiers</small></div></div><span className="chip">SYSTEM ID</span></div>
        <div className="grid2" style={{ marginTop: 16 }}>
          <label className="field"><span>User Identifier</span><input readOnly value={userId} /></label>
          <label className="field"><span>Applicant UUID</span><input readOnly value={score.applicant_id || ''} /></label>
        </div>
      </section>

      {SECTIONS.map((s) => (
        <section className="card" key={s.title}>
          <div className="row between"><div className="row"><span className="section-icon"><Icon name={s.icon} /></span><div><h3>{s.title}</h3><small>{s.desc}</small></div></div><span className="chip chip-pos">{s.tag}</span></div>
          <div className="form-grid" style={{ marginTop: 16 }}>
            {s.fields.map(([k, label, hint, type, x]) => (
              <label className="field" key={k}><span>{label}<small>{hint}</small></span>
                {type === 'number' && <input type="number" inputMode="decimal" {...x} value={form[k]} onChange={setK(k)} />}
                {type === 'select' && <select value={form[k]} onChange={setK(k)}>{form[k] === '' && <option value="">—</option>}{x.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>}
                {type === 'edu' && <select value={form[k]} onChange={setK(k)}>{form[k] === '' && <option value="">—</option>}{eduOptions.map((o) => <option key={o}>{o}</option>)}</select>}
              </label>
            ))}
          </div>
        </section>
      ))}

      {err && <div className="err" role="alert">{err}</div>}
      <div className="cta wrap"><Icon name="query_stats" /><div style={{ flex: 1, minWidth: 200 }}><strong>Ready to project the updated model?</strong><br /><small>Adjusting parameters re-scores your profile with the live rule engine.</small></div>
        <button className="btn btn-ghost" onClick={reset}>Reset to Baseline</button>
        <button className="btn btn-primary" onClick={recalc} disabled={busy}><Icon name="refresh" /> {busy ? 'Calculating…' : 'Recalculate Projected Score'}</button></div>
    </>
  )
}

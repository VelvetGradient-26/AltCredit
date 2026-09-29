import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { Bar, ErrorBox, Icon, ScoreRing, Spinner, fmt, tierMeta, useLoad } from '../components/ui'

// pillar maxima from machine_learning/engines/config.py comments
const PILLARS = [
  { key: 'lifestyle_score', label: 'Lifestyle', max: 350 },
  { key: 'spending_behavior_score', label: 'Spending', max: 350 },
  { key: 'repayment_discipline_score', label: 'Repayment Discipline', max: 570 },
]

function jsonToCsv(text) {
  const rows = JSON.parse(text)
  const list = Array.isArray(rows) ? rows : rows.transactions
  if (!Array.isArray(list) || !list.length) throw new Error('JSON must be a list of transactions')
  const cols = [...new Set(list.flatMap(Object.keys))]
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
  return [cols.join(','), ...list.map((r) => cols.map((c) => esc(r[c])).join(','))].join('\n')
}

export default function Dashboard() {
  const { userId } = useAuth()
  const { data: d, error, loading, reload } = useLoad(() => api.dashboard(userId), [userId])
  const [upload, setUpload] = useState(null)   // {name,size,state,msg}
  const [over, setOver] = useState(false)
  const input = useRef()

  const send = async (file) => {
    if (!file) return
    setUpload({ name: file.name, size: file.size, state: 'busy' })
    try {
      let f = file
      if (/\.json$/i.test(file.name)) f = new File([jsonToCsv(await file.text())], file.name.replace(/\.json$/i, '.csv'), { type: 'text/csv' })
      const r = await api.uploadTransactions(userId, f)
      setUpload({ name: file.name, size: file.size, state: 'ok', msg: `${r.transactions_read} transactions parsed · score ${fmt(r.credit_score)}` })
      reload()
    } catch (e) { setUpload({ name: file.name, size: file.size, state: 'err', msg: e.message }) }
  }

  const [dl, setDl] = useState({})     // {pdf|json: 'busy' | error message}
  const save = async (kind) => {
    setDl((s) => ({ ...s, [kind]: 'busy' }))
    try {
      const blob = await (kind === 'pdf' ? api.reportPdf(userId) : api.exportJson(userId))
      const url = URL.createObjectURL(blob)
      const a = Object.assign(document.createElement('a'), { href: url, download: `altcredit_${kind === 'pdf' ? 'report' : 'profile'}_${userId}.${kind}` })
      document.body.appendChild(a); a.click(); a.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      setDl((s) => ({ ...s, [kind]: '' }))
    } catch (e) { setDl((s) => ({ ...s, [kind]: e.message })) }
  }
  const [ai, setAi] = useState(null)       // {state:'busy'|'ok'|'err', data, msg}
  const explain = async () => {
    setAi({ state: 'busy' })
    try { setAi({ state: 'ok', data: await api.explain(userId) }) }
    catch (e) { setAi({ state: 'err', msg: e.message }) }
  }

  if (loading && !d) return <Spinner />
  if (error) return <ErrorBox error={error} retry={reload} />
  const t = tierMeta(d.score.risk_tier)
  const pos = d.credit_drivers.top_positive
  const attention = [...d.credit_drivers.negative, ...d.credit_drivers.weak].sort((a, b) => b.max_score - a.max_score).slice(0, 5)

  return (
    <>
      <div><h1>Hello, {userId}</h1><p className="muted">Here’s your current ALTcredit profile.</p></div>

      <section className="card hero">
        <ScoreRing value={d.score.value} colour={t.colour} size={112}><Icon name="verified" /></ScoreRing>
        <div>
          <div className="label">ALTcredit score</div>
          <div className="score-num">{fmt(d.score.value)}<small className="muted">/ {d.score.max}</small></div>
          <small>Estimated default risk {(d.score.predicted_pd * 100).toFixed(1)}%</small>
        </div>
        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
          <span className={`chip ${t.chip}`} style={{ fontSize: 14 }}>{d.score.risk_tier}</span>
          <div className="muted" style={{ marginTop: 8, maxWidth: 280 }}>{d.score.decision_reason}</div>
          <button className="btn btn-navy btn-sm" style={{ marginTop: 12 }} disabled={dl.pdf === 'busy'} onClick={() => save('pdf')}><Icon name="picture_as_pdf" /> {dl.pdf === 'busy' ? 'Preparing…' : 'Download PDF report'}</button>
          {dl.pdf && dl.pdf !== 'busy' && <div className="err" role="alert" style={{ marginTop: 8 }}>{dl.pdf}</div>}
        </div>
      </section>

      <section>
        <h2 style={{ marginBottom: 12 }}>Score Breakdown</h2>
        <div className="grid3">
          {PILLARS.map((p, i) => {
            const v = d.pillars[p.key]
            const colour = v / p.max >= 0.6 ? 'var(--emerald)' : v / p.max >= 0.4 ? 'var(--amber)' : 'var(--coral)'
            return (
              <div className="card pillar" key={p.key}>
                <div className="row between"><span style={{ fontWeight: 600 }}>{p.label}</span><strong>{v}</strong></div>
                <Bar value={v} max={p.max} colour={colour} />
                <small>out of {p.max}{i === 0 && d.pillars.net_adjustments ? ` · adjustments ${d.pillars.net_adjustments > 0 ? '+' : ''}${d.pillars.net_adjustments}` : ''}</small>
              </div>
            )
          })}
        </div>
      </section>

      <section className="card">
        <div className="row between wrap"><div><h2>Update Your Financial Data</h2><p className="muted">Upload a bank statement (CSV or JSON: date, amount, category, type, status).</p></div>
          <small><Icon name="info" /> Supported: JSON, CSV</small></div>
        <div className="grid2" style={{ marginTop: 16 }}>
          <div className={`drop ${over ? 'over' : ''}`} onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); send(e.dataTransfer.files[0]) }}>
            <Icon name="upload_file" />
            <strong>Drag & drop statement here</strong><small>or</small>
            <button className="btn btn-tint btn-sm" onClick={() => input.current.click()}>Browse / Upload</button>
            <input ref={input} type="file" accept=".csv,.json" hidden onChange={(e) => { send(e.target.files[0]); e.target.value = '' }} />
          </div>
          <div className="file-card" aria-live="polite">
            {!upload && <div className="muted">No statement uploaded this session. Your score currently uses the profile on file{d.missing_fields.length ? ` (${d.missing_fields.length} inputs missing)` : ''}.</div>}
            {upload && <>
              <div className="row"><span className="section-icon"><Icon name="description" /></span><div><strong>{upload.name}</strong><br /><small>{(upload.size / 1024).toFixed(1)} KB</small></div></div>
              {upload.state === 'busy' && <Spinner label="Parsing & scoring…" />}
              {upload.state === 'ok' && <div style={{ color: 'var(--emerald-d)' }}><Icon name="check_circle" /> {upload.msg}</div>}
              {upload.state === 'err' && <div className="err">{upload.msg}</div>}
            </>}
          </div>
        </div>
      </section>

      <section className="card">
        <div className="row between wrap"><div><h2><Icon name="auto_awesome" /> AI explanation</h2><p className="muted">A plain-language walk-through of your score, written by an AI from your factor breakdown. The numbers always come from the rule engine.</p></div>
          <button className="btn btn-primary" disabled={ai?.state === 'busy'} onClick={explain}>{ai?.state === 'busy' ? 'Explaining…' : ai?.state === 'ok' ? 'Regenerate' : 'Explain my score'}</button></div>
        {ai?.state === 'busy' && <Spinner label="Writing your explanation…" />}
        {ai?.state === 'err' && <div className="err" role="alert" style={{ marginTop: 12 }}>{ai.msg} <button className="link" onClick={explain}>Retry</button></div>}
        {ai?.state === 'ok' && <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <p>{ai.data.summary}</p>
          <div className="grid2">
            <div><div className="label" style={{ color: 'var(--emerald-dd)', marginBottom: 8 }}>Strengths</div><ul>{ai.data.strengths.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
            <div><div className="label" style={{ color: '#b45309', marginBottom: 8 }}>Weaknesses</div><ul>{ai.data.weaknesses.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
          </div>
          <div><div className="label" style={{ marginBottom: 8 }}>Next steps</div><ol>{ai.data.next_steps.map((x, i) => <li key={i}>{x}</li>)}</ol></div>
          <small className="muted">Generated by {ai.data.model}. Explanation only, not financial advice.</small>
        </div>}
      </section>

      <section className="card">
        <h2>Why is my score this way?</h2><p className="muted" style={{ marginBottom: 16 }}>Transparent breakdown of the factors influencing your score.</p>
        <div className="grid2">
          <div><div className="label" style={{ color: 'var(--emerald-dd)', marginBottom: 12 }}>Positive factors</div>
            {pos.map((f) => <div className="factor" key={f.factor_key}><Icon name="check" /><div><strong>{f.factor}</strong><small>{f.explanation}</small></div><span className="pts" style={{ color: 'var(--emerald-d)' }}>+{f.score}</span></div>)}
            {!pos.length && <p className="muted">No positive factors yet.</p>}</div>
          <div><div className="label" style={{ color: '#b45309', marginBottom: 12 }}>Needs attention</div>
            {attention.map((f) => <div className="factor warn" key={f.factor_key}><Icon name="priority_high" /><div><strong>{f.factor}</strong><small>{f.explanation} Up to {Math.abs(f.max_score)} pts available.</small></div><span className="pts" style={{ color: '#b45309' }}>{f.score}</span></div>)}
            {!attention.length && <p className="muted">Nothing needs attention — great work.</p>}</div>
        </div>
      </section>

      {d.has_pending_offers && <Link to="/recommendations" className="card row between" style={{ textDecoration: 'none', color: 'inherit', borderColor: 'var(--emerald)' }}>
        <span><Icon name="mark_email_unread" /> <strong>You have new lender offers waiting.</strong></span><span className="link">Review →</span></Link>}

      <div className="grid2">
        <div className="card"><h2>What-If Simulator</h2><p className="muted" style={{ margin: '4px 0 16px' }}>See how your financial decisions could affect your score.</p><Link className="btn btn-primary" to="/simulator">Try Simulator</Link></div>
        <div className="card"><h2>Recommended Products</h2><p className="muted" style={{ margin: '4px 0 16px' }}>{d.next_steps.eligible_products.length} product(s) match your score today.</p><Link className="btn btn-tint" to="/recommendations">View Recommendations</Link></div>
      </div>

      <section className="card row between wrap"><div><h2>Your ALTcredit Report</h2><p className="muted">Download your current score decision and factor analysis.</p>
        {(dl.pdf || dl.json) && [dl.pdf, dl.json].filter((m) => m && m !== 'busy').map((m) => <div key={m} className="err" role="alert">{m}</div>)}</div>
        <div className="row"><button className="btn btn-ghost" disabled={dl.json === 'busy'} onClick={() => save('json')}><Icon name="data_object" /> Export JSON</button>
          <button className="btn btn-navy" disabled={dl.pdf === 'busy'} onClick={() => save('pdf')}><Icon name="download" /> Download PDF</button></div></section>

      <p className="disclaimer">ALTcredit is a prototype alternative credit scoring system using synthetic data. This score is an estimate for demonstration purposes and is not an official credit bureau score. Product recommendations are indicative and do not guarantee approval.</p>
    </>
  )
}

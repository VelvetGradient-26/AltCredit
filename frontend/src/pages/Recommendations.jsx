import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { ErrorBox, Icon, Modal, Spinner, fmt, tierMeta, useLoad } from '../components/ui'

const TABS = [['all', 'All Products'], ['Credit Card', 'Credit Cards'], ['Loan', 'Loans']]

export default function Recommendations() {
  const { userId } = useAuth()
  const { data, error, loading, reload } = useLoad(
    () => Promise.all([api.recommendations(userId), api.userOffers(userId), api.score(userId)]), [userId])
  const [tab, setTab] = useState('all')
  const [sort, setSort] = useState('high')
  const [modal, setModal] = useState(null)   // {kind:'apply'|'plan', product, result}
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState('')

  if (loading && !data) return <Spinner />
  if (error) return <ErrorBox error={error} retry={reload} />
  const [recs, offers, score] = data
  const t = tierMeta(score.risk_tier)

  const all = [
    ...recs.eligible_products.map((p) => ({ ...p.product_details, eligible: true, margin: p.points_above_requirement })),
    ...recs.ineligible_products.map((p) => ({ ...p.product_details, eligible: false, needed: p.points_needed })),
  ]
  const list = all.filter((p) => tab === 'all' || p.type === tab).sort((a, b) => (sort === 'high' ? b.min_score - a.min_score : a.min_score - b.min_score))
  const flash = (m) => { setToast(m); setTimeout(() => setToast(''), 3000) }

  const apply = async (p) => {
    setBusy(true)
    try { setModal({ kind: 'apply', product: p, result: await api.apply(userId, p.product_id) }) }
    catch (e) { setModal({ kind: 'apply', product: p, error: e.message }) } finally { setBusy(false) }
  }
  const plan = async (p) => {
    setModal({ kind: 'plan', product: p, loading: true })
    try { setModal({ kind: 'plan', product: p, plan: await api.target(userId, p.product_id) }) }
    catch (e) { setModal({ kind: 'plan', product: p, error: e.message }) }
  }
  const respond = async (id, decision) => {
    try { await api.respondOffer(userId, id, decision); flash(`Offer ${decision.toLowerCase()}`); reload() } catch (e) { flash(e.message) }
  }
  const open = offers.filter((o) => o.status === 'OFFERED')

  return (
    <>
      <section className="card row between wrap" style={{ background: 'linear-gradient(120deg,#fff,#ecfdf5)' }}>
        <div style={{ maxWidth: 620 }}>
          <span className="chip chip-pos">Cashflow engine active</span>
          <h1 style={{ margin: '10px 0' }}>Recommended Products for You</h1>
          <p className="muted">Matched to your <b>{fmt(score.credit_score)}</b> ALTcredit score. Pre-screened using alternative cashflow indicators — no bureau history needed.</p>
        </div>
        <div className="card" style={{ minWidth: 220 }}>
          <div className="label">Matched tier</div><span className={`chip ${t.chip}`} style={{ margin: '6px 0' }}>{score.risk_tier}</span>
          <div><b>{recs.eligible_products.length}</b> of {all.length} products unlocked</div>
        </div>
      </section>

      {offers.length > 0 && (
        <section className="card">
          <h2>Offers from lenders</h2><p className="muted" style={{ marginBottom: 8 }}>Your identity stays hidden from a lender until you accept its offer.</p>
          {offers.map((o) => (
            <div key={o.offer_id} className="step row between wrap">
              <div><strong>{o.lender}</strong> · {o.offer_type}<br /><small>{fmt(o.loan_amount)} at {o.interest_rate}% p.a.</small></div>
              {o.status === 'OFFERED'
                ? <div className="row"><button className="btn btn-primary btn-sm" onClick={() => respond(o.offer_id, 'ACCEPTED')}>Accept</button><button className="btn btn-ghost btn-sm" onClick={() => respond(o.offer_id, 'DECLINED')}>Decline</button></div>
                : <span className={`chip ${o.status === 'ACCEPTED' ? 'chip-pos' : ''}`}>{o.status}</span>}
            </div>))}
          {open.length === 0 && <small>No open offers.</small>}
        </section>
      )}

      <div className="row between wrap">
        <div className="tabs" role="tablist">{TABS.map(([k, l]) => <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l} ({k === 'all' ? all.length : all.filter((p) => p.type === k).length})</button>)}</div>
        <label className="row"><small>Sort by</small><select style={{ width: 200 }} value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="high">Score requirement (highest)</option><option value="low">Score requirement (lowest)</option></select></label>
      </div>

      <div className="grid2">
        {list.map((p) => (
          <article key={p.product_id} className="card product">
            <div className="row between">
              <div className="row"><span className="section-icon"><Icon name={p.type === 'Credit Card' ? 'credit_card' : 'account_balance'} /></span>
                <div><small className="label">{p.type}</small><h3>{p.product_name}</h3></div></div>
              {p.eligible ? <span className="chip chip-pos"><Icon name="verified" />Pre-screen eligible</span> : <span className="chip chip-warn"><Icon name="lock" />+{fmt(p.needed)} pts needed</span>}
            </div>
            <div className="metrics">
              <div><small>Indicative rate</small><b>{p.interest_rate}</b></div>
              <div><small>Min. score</small><b>{p.min_score}</b></div>
              <div><small>{p.eligible ? 'Your margin' : 'Your score'}</small><b>{p.eligible ? `+${fmt(p.margin)}` : fmt(score.credit_score)}</b></div>
            </div>
            <ul className="checks">
              <li><Icon name="check_circle" />{p.eligible ? 'Your score clears the requirement' : `Need ${fmt(p.needed)} more points to qualify`}</li>
              <li><Icon name="check_circle" />Soft check only — no bureau inquiry</li>
            </ul>
            <div className="row between" style={{ marginTop: 'auto' }}>
              <small>Final terms set by the partner bank</small>
              {p.eligible
                ? <button className="btn btn-dark" disabled={busy} onClick={() => apply(p)}>Apply with Provider <Icon name="open_in_new" /></button>
                : <button className="btn btn-tint" onClick={() => plan(p)}>How to qualify <Icon name="route" /></button>}
            </div>
          </article>
        ))}
      </div>
      {!list.length && <div className="state">No products in this category.</div>}

      <section className="cta wrap"><Icon name="query_stats" /><div style={{ flex: 1, minWidth: 220 }}><strong>How is the match computed?</strong><br />
        <small>Your score comes from rule-based alternative factors (payments, cashflow, savings, stability). A product is eligible when your score meets its minimum.</small></div>
        <Link to="/simulator" className="btn btn-ghost">Simulate Score Impact <Icon name="tune" /></Link></section>
      <p className="disclaimer">“Recommended” and “Pre-screen eligible” are synthetic suitability indicators, not guaranteed approval or credit extension. Final terms remain at the sole discretion of the partner bank.</p>

      {modal?.kind === 'apply' && (
        <Modal title={modal.product.product_name} onClose={() => { setModal(null); reload() }}>
          {modal.error && <div className="err">{modal.error}</div>}
          {modal.result && (modal.result.status === 'APPROVED' ? <>
            <div className="chip chip-pos" style={{ alignSelf: 'flex-start' }}><Icon name="check_circle" />Pre-approved by partner bank</div>
            {Object.entries(modal.result.details).map(([k, v]) => <div key={k} className="row between"><span className="muted">{k.replace(/_/g, ' ')}</span><b>{typeof v === 'number' ? fmt(v) : v}</b></div>)}
            <div className="row between"><span className="muted">Reference</span><b className="mono">{modal.result.bank_reference}</b></div>
          </> : <div className="err">Declined: {modal.result.reason}</div>)}
          <button className="btn btn-navy" onClick={() => { setModal(null); reload() }}>Done</button>
        </Modal>
      )}
      {modal?.kind === 'plan' && (
        <Modal title={`Path to ${modal.product.product_name}`} onClose={() => setModal(null)} wide>
          {modal.loading && <Spinner label="Computing the smallest changes…" />}
          {modal.error && <div className="err">{modal.error}</div>}
          {modal.plan && <>
            <p>{modal.plan.summary}</p>
            <div className="row"><b>{fmt(modal.plan.current_score)}</b><Icon name="arrow_forward" /><b style={{ color: 'var(--emerald-d)' }}>{fmt(modal.plan.projected_score)}</b><small>(target {modal.plan.target_score})</small></div>
            {modal.plan.steps.map((s) => (
              <div className="step" key={s.feature}><Icon name="flag" /><div><strong>{s.action}</strong><br /><small>{s.advice}</small></div><span className="pts pill-up" style={{ marginLeft: 'auto', background: 'rgba(16,185,129,.12)', color: 'var(--emerald-d)' }}>+{s.points_gain}</span></div>))}
            <Link className="btn btn-primary" to="/simulator" onClick={() => setModal(null)}>Try it in the simulator</Link>
          </>}
        </Modal>
      )}
      {toast && <div className="toast" role="status">{toast}</div>}
    </>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { Bar, ErrorBox, Icon, Modal, Spinner, fmt, tierMeta, useLoad } from '../components/ui'

const LIMIT = 10
const DEFAULT_RULES = { min_score: 0, min_income: '', max_dti: '', max_pd: '', only_qualifying: false }

export default function Lender() {
  const { logout, userId: lenderId } = useAuth()
  const nav = useNavigate()
  const me = useLoad(() => api.lenderMe(lenderId), [lenderId])
  const [view, setView] = useState('pipeline')
  const [rules, setRules] = useState(DEFAULT_RULES)
  const [applied, setApplied] = useState(DEFAULT_RULES)
  const [page, setPage] = useState(0)
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(new Set())
  const [res, setRes] = useState({ loading: true })
  const [pool, setPool] = useState(null)
  const [modal, setModal] = useState(null)
  const [offersTick, setOffersTick] = useState(0)
  const offers = useLoad(() => api.lenderOffers(lenderId), [offersTick, lenderId])

  const fetchPage = useCallback(() => {
    setRes((r) => ({ ...r, loading: true }))
    const { min_score, ...rest } = applied
    api.candidates(lenderId, { ...rest, q: q.trim(), min_score: min_score || '', sort: 'score_desc', limit: LIMIT, offset: page * LIMIT })
      .then((data) => setRes({ data }), (error) => setRes({ error }))
  }, [applied, page, lenderId, q])
  useEffect(() => { const t = setTimeout(fetchPage, q ? 250 : 0); return () => clearTimeout(t) }, [fetchPage])
  // rules apply automatically shortly after the last edit; the button just applies immediately
  useEffect(() => { const t = setTimeout(() => { setApplied(rules); setPage(0) }, 500); return () => clearTimeout(t) }, [rules])
  useEffect(() => { api.candidates(lenderId, { only_qualifying: false, limit: 1 }).then((d) => setPool(d.total), () => {}) }, [lenderId])

  const apply = () => { setApplied(rules); setPage(0) }
  const onSearch = (e) => { setQ(e.target.value); setPage(0) }
  const reset = () => { setRules(DEFAULT_RULES); setApplied(DEFAULT_RULES); setPage(0) }
  const rows = res.data?.results || []
  const toggle = (id) => setSel((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  const allShown = rows.length > 0 && rows.every((c) => sel.has(c.anon_lead_id))
  const toggleAll = () => setSel((s) => { const n = new Set(s); rows.forEach((c) => (allShown ? n.delete(c.anon_lead_id) : n.add(c.anon_lead_id))); return n })
  const pages = Math.max(1, Math.ceil((res.data?.total || 0) / LIMIT))
  const list = offers.data || []
  const accepted = list.filter((o) => o.status === 'ACCEPTED').length
  const upd = (k) => (e) => setRules({ ...rules, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  return (
    <div className="lshell">
      <aside className="sidebar">
        <div className="row"><span className="brand-mark" style={{ background: 'var(--emerald-dd)', color: '#fff', fontWeight: 700 }}>{(me.data?.company_name || 'A')[0]}</span>
          <div><Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}><strong style={{ fontFamily: 'var(--head)' }}>ALTcredit</strong></Link><br /><small className="label">Lender portal</small></div></div>
        {me.data && <div className="card" style={{ padding: 16 }}><div className="label">Your policy</div>
          <div className="row between" style={{ marginTop: 8 }}><span>Min score</span><b>{me.data.min_credit_score_requirement}</b></div>
          <div className="row between"><span>Max PD</span><b>{(me.data.max_pd_threshold * 100).toFixed(0)}%</b></div></div>}
        <nav>
          <button className={`nav-item ${view === 'pipeline' ? 'active' : ''}`} onClick={() => setView('pipeline')}><Icon name="group_search" />Candidate Search</button>
          <button className={`nav-item ${view === 'offers' ? 'active' : ''}`} onClick={() => setView('offers')}><Icon name="campaign" />Offer Campaigns
            {list.length > 0 && <span className="chip chip-pos" style={{ marginLeft: 'auto' }}>{list.length}</span>}</button>
        </nav>
        <div className="card row" style={{ padding: 14 }}><Icon name="business" /><div><strong>{me.data?.company_name}</strong><br /><small>Verified lender</small></div></div>
        <button className="nav-item logout" onClick={() => { logout(); nav('/login') }}><Icon name="logout" />Logout</button>
      </aside>

      <div className="lmain">
        <header className="topbar">
          <div className="input-icon" style={{ flex: 1, maxWidth: 480 }}><Icon name="search" /><input placeholder="Search all candidates by token, e.g. ANON-98A4…" value={q} onChange={onSearch} aria-label="Search candidates" /></div>
          <span className="chip chip-pos"><i className="dot" style={{ background: 'var(--emerald)' }} />Anonymised data only</span>
          <div className="who"><div><strong>{me.data?.company_name}</strong><small>Lender user</small></div><span className="avatar"><Icon name="account_balance" /></span></div>
        </header>
        <main className="content">
          <div><h1>Institutional Desk</h1><p className="muted">Browse anonymised candidates, assess risk profiles and push pre-approved offers. Identities are revealed only after a candidate accepts.</p></div>

          <div className="stats">
            <div className="card stat"><span className="label">Candidate pool</span><b>{fmt(pool)}</b><small>Anonymised, active leads</small></div>
            <div className="card stat"><span className="label">Filtered matches</span><b>{fmt(res.data?.total)}</b><small>{applied.only_qualifying ? 'Meeting your policy' : 'All candidates'}</small></div>
            <div className="card stat"><span className="label">Dispatched offers</span><b>{list.length}</b><small>{list.filter((o) => o.status === 'OFFERED').length} awaiting response</small></div>
            <div className="card stat"><span className="label">Accepted</span><b>{accepted}</b><small>{list.length ? `${((accepted / list.length) * 100).toFixed(0)}% conversion` : 'No offers yet'}</small></div>
          </div>

          {view === 'pipeline' && (
            <div className="lbody">
              <aside className="card">
                <div className="row between"><h3><Icon name="filter_alt" /> Sourcing Rules</h3><button className="link" onClick={reset}>Reset</button></div>
                <div className="rule"><div className="row between"><span className="label">AltCredit score floor</span><b>{rules.min_score}–1000</b></div>
                  <input type="range" min="0" max="1000" step="10" value={rules.min_score} onChange={upd('min_score')} aria-label="Score floor" />
                  <div className="row between"><small>0 High risk</small><small>550</small><small>650</small><small>750+</small></div></div>
                <label className="field rule"><span>Min monthly income</span><input type="number" min="0" placeholder="e.g. 2500" value={rules.min_income} onChange={upd('min_income')} /></label>
                <label className="field rule"><span>Max debt-to-income <small>ratio</small></span><input type="number" min="0" step="0.05" placeholder="e.g. 0.35" value={rules.max_dti} onChange={upd('max_dti')} /></label>
                <label className="field rule"><span>Max default probability <small>0–1</small></span><input type="number" min="0" max="1" step="0.05" placeholder="e.g. 0.3" value={rules.max_pd} onChange={upd('max_pd')} /></label>
                <label className="row rule"><input type="checkbox" checked={rules.only_qualifying} onChange={upd('only_qualifying')} /> Only candidates meeting my lending policy</label>
                <button className="btn btn-dark" style={{ width: '100%', marginTop: 18 }} onClick={apply}><Icon name="task_alt" /> Apply Filters</button>
              </aside>

              <section className="card" style={{ padding: 0 }}>
                <div className="row between wrap" style={{ padding: 16 }}>
                  <label className="row"><input type="checkbox" checked={allShown} onChange={toggleAll} /> Select all displayed <small>· {sel.size} selected</small></label>
                  <button className="btn btn-dark" disabled={!sel.size} onClick={() => setModal({ kind: 'push' })}><Icon name="bolt" /> Create Bulk Push Campaign ({sel.size})</button>
                </div>
                {res.error ? <ErrorBox error={res.error} retry={fetchPage} /> : res.loading && !res.data ? <Spinner /> : (
                  <div className="tbl-wrap"><table>
                    <thead><tr><th></th><th>Candidate</th><th>ALTcredit score</th><th>Default prob.</th><th>Monthly income</th><th>DTI</th><th></th></tr></thead>
                    <tbody>{rows.map((c) => { const t = tierMeta(c.risk_tier); return (
                      <tr key={c.anon_lead_id}>
                        <td><input type="checkbox" checked={sel.has(c.anon_lead_id)} onChange={() => toggle(c.anon_lead_id)} aria-label={`Select ${c.anon_lead_id}`} /></td>
                        <td><b className="mono" style={{ color: 'var(--navy)', fontSize: 13 }}>{c.anon_lead_id}</b></td>
                        <td><b style={{ fontSize: 18 }}>{c.credit_score}</b> <span className={`chip ${t.chip}`}>{c.risk_tier.split(' /')[0]}</span></td>
                        <td>{(c.predicted_pd * 100).toFixed(1)}%</td><td>{fmt(c.monthly_income)}</td><td>{(c.debt_to_income * 100).toFixed(0)}%</td>
                        <td><button className="btn btn-tint btn-sm" onClick={() => setModal({ kind: 'detail', id: c.anon_lead_id })}><Icon name="analytics" /> Evaluate</button></td>
                      </tr>) })}</tbody>
                  </table>{!rows.length && !res.loading && <div className="state">No candidates match these rules.</div>}</div>)}
                <div className="pager" style={{ padding: 16 }}>
                  <small>Showing {res.data?.total ? page * LIMIT + 1 : 0}–{Math.min((page + 1) * LIMIT, res.data?.total || 0)} of {fmt(res.data?.total)} profiles</small>
                  <div className="row"><button className="btn btn-ghost btn-sm" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button><span>{page + 1} / {pages}</span>
                    <button className="btn btn-ghost btn-sm" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>Next</button></div>
                </div>
              </section>
            </div>
          )}

          {view === 'offers' && (
            <section className="card">
              <h2>Offer campaigns</h2>
              {offers.loading && !offers.data ? <Spinner /> : offers.error ? <ErrorBox error={offers.error} retry={offers.reload} /> : (
                <div className="tbl-wrap"><table>
                  <thead><tr><th>Offer</th><th>Candidate</th><th>Type</th><th>Amount</th><th>Rate</th><th>Status</th><th>Contact</th></tr></thead>
                  <tbody>{list.map((o) => (
                    <tr key={o.offer_id}><td>#{o.offer_id}</td><td className="mono">{o.anon_lead_id}</td><td>{o.offer_type}</td><td>{fmt(o.loan_amount)}</td><td>{o.interest_rate}%</td>
                      <td><span className={`chip ${o.status === 'ACCEPTED' ? 'chip-pos' : o.status === 'DECLINED' ? 'chip-bad' : 'chip-warn'}`}>{o.status}</span></td>
                      <td>{o.contact ? <><b>{o.contact.full_name}</b><br /><small>{o.contact.email}</small></> : <small><Icon name="lock" /> Hidden until accepted</small>}</td></tr>))}</tbody>
                </table>{!list.length && <div className="state">No offers dispatched yet.</div>}</div>)}
            </section>
          )}
        </main>
      </div>

      {modal?.kind === 'detail' && <Detail lenderId={lenderId} id={modal.id} onClose={() => setModal(null)} onPush={() => { setSel(new Set([modal.id])); setModal({ kind: 'push' }) }} />}
      {modal?.kind === 'push' && <Push lenderId={lenderId} ids={[...sel]} onClose={() => setModal(null)} onDone={() => { setSel(new Set()); setOffersTick((n) => n + 1) }} />}
    </div>
  )
}

function Detail({ lenderId, id, onClose, onPush }) {
  const { data: d, error, loading } = useLoad(() => api.candidate(lenderId, id), [id, lenderId])
  const P = [['lifestyle_score', 'Lifestyle', 350], ['spending_behavior_score', 'Spending', 350], ['repayment_discipline_score', 'Repayment', 570]]
  return (
    <Modal title={`Risk dossier · ${id}`} onClose={onClose} wide>
      {loading && <Spinner />}{error && <ErrorBox error={error} />}
      {d && <>
        <div className="row wrap"><b style={{ fontSize: 40, fontFamily: 'var(--head)' }}>{d.credit_score}</b><span className={`chip ${tierMeta(d.risk_tier).chip}`}>{d.risk_tier}</span>
          <span className={`chip ${d.qualifies ? 'chip-pos' : 'chip-warn'}`}>{d.qualifies ? 'Meets your policy' : 'Below your policy'}</span></div>
        <div className="grid3" style={{ gap: 12 }}>{P.map(([k, l, m]) => <div key={k}><div className="row between"><small>{l}</small><b>{d.pillar_breakdown[k]}</b></div><Bar value={d.pillar_breakdown[k]} max={m} /></div>)}</div>
        <div className="tbl-wrap"><table><thead><tr><th>Factor</th><th>Observed</th><th>Points</th></tr></thead>
          <tbody>{Object.entries(d.subfactors).map(([k, f]) => <tr key={k}><td>{k.replace(/^\d\.\d_/, '').replace(/_/g, ' ')}</td><td>{f.val}</td><td>{f.score} / {f.max}</td></tr>)}</tbody></table></div>
        <button className="btn btn-dark" disabled={!d.qualifies} onClick={onPush}><Icon name="send" /> Push offer to this candidate</button>
      </>}
    </Modal>
  )
}

function Push({ lenderId, ids, onClose, onDone }) {
  const [f, setF] = useState({ offer_type: 'Loan', loan_amount: 25000, interest_rate: 14 })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [out, setOut] = useState(null)
  const go = async () => {
    setBusy(true); setErr('')
    try { setOut(await api.pushOffers(lenderId, { anon_lead_ids: ids, offer_type: f.offer_type, loan_amount: Number(f.loan_amount), interest_rate: Number(f.interest_rate) })); onDone() }
    catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <Modal title={`Push offer to ${ids.length} candidate${ids.length > 1 ? 's' : ''}`} onClose={onClose}>
      {!out ? <>
        <label className="field"><span>Offer type</span><select value={f.offer_type} onChange={(e) => setF({ ...f, offer_type: e.target.value })}><option>Loan</option><option>Credit Card</option></select></label>
        <label className="field"><span>{f.offer_type === 'Loan' ? 'Loan amount' : 'Credit limit'}</span><input type="number" min="1" value={f.loan_amount} onChange={(e) => setF({ ...f, loan_amount: e.target.value })} /></label>
        <label className="field"><span>Interest rate <small>% p.a.</small></span><input type="number" min="0.1" max="100" step="0.1" value={f.interest_rate} onChange={(e) => setF({ ...f, interest_rate: e.target.value })} /></label>
        <small>Candidates outside your lending policy are skipped automatically.</small>
        {err && <div className="err">{err}</div>}
        <button className="btn btn-dark" disabled={busy} onClick={go}>{busy ? 'Sending…' : 'Dispatch offers'}</button>
      </> : <>
        <div className="chip chip-pos" style={{ alignSelf: 'flex-start' }}><Icon name="check_circle" />{out.created.length} offer(s) dispatched</div>
        {out.skipped.map((s) => <div key={s.anon_lead_id} className="row between"><span className="mono">{s.anon_lead_id}</span><small>{s.reason}</small></div>)}
        <button className="btn btn-navy" onClick={onClose}>Done</button>
      </>}
    </Modal>
  )
}

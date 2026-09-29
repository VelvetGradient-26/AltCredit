import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { Brand } from '../components/Layout'
import { Bar, Icon, ScoreRing } from '../components/ui'
import './landing.css'

const STEPS = [
  { icon: 'person_add', title: 'Create your profile', text: 'Tell us about your work, housing and money habits. No loan or credit card history needed.' },
  { icon: 'upload_file', title: 'Add your data', text: 'Optionally upload a bank statement. We read payments, spending and savings, not your name or account number.' },
  { icon: 'speed', title: 'Get scored instantly', text: 'A 0–1000 score, a plain-language explanation and products you already qualify for.' },
]

const FEATURES = [
  { icon: 'fact_check', title: 'Explainable, factor by factor', text: 'Every score is 14 visible factors. See exactly which habits earned or cost you points.' },
  { icon: 'tune', title: 'What-if simulator', text: 'Try saving more, paying on time or taking on debt and watch the projected score move before you act.' },
  { icon: 'flag', title: 'Path to your next product', text: 'Pick a card or loan and get the smallest set of changes that would unlock it.' },
  { icon: 'account_balance', title: 'Pre-approved offers', text: 'Eligible products connect to partner banks through an API for a pre-approval in one click.' },
  { icon: 'picture_as_pdf', title: 'Transparency report', text: 'Download a PDF that explains the decision, or export your credit profile as JSON.' },
  { icon: 'shield_person', title: 'Private by design', text: 'Lenders browse anonymous profiles. Your identity is revealed only if you accept their offer.' },
]

const BANDS = [
  { range: '750 – 1000', name: 'Prime', note: 'Low risk', colour: '#10B981' },
  { range: '650 – 749', name: 'Near-Prime', note: 'Medium risk', colour: '#0284C7' },
  { range: '550 – 649', name: 'Sub-Prime', note: 'Fair', colour: '#F59E0B' },
  { range: '0 – 549', name: 'High risk', note: 'Needs work', colour: '#EF4444' },
]

const PILLARS = [
  { name: 'Lifestyle', icon: 'home', items: ['Employment stability', 'Housing status', 'Digital bill payments', 'Education'] },
  { name: 'Spending behaviour', icon: 'account_balance_wallet', items: ['Spend-to-income ratio', 'Essentials vs discretionary', 'Cash-flow volatility', 'Savings buffer'] },
  { name: 'Repayment discipline', icon: 'history', items: ['On-time payment rate', 'Debt-to-income', 'Credit utilisation', 'Recent delinquency'] },
]

export default function Landing() {
  const { role, logout } = useAuth()
  const nav = useNavigate()
  const home = role === 'lender' ? '/lender' : '/dashboard'
  return (
    <div className="landing">
      <header className="l-nav">
        <Brand />
        <nav className="l-links" aria-label="Sections">
          <a href="#how">How it works</a><a href="#features">Features</a><a href="#score">The score</a><a href="#lenders">For lenders</a>
        </nav>
        <div className="row">
          {role ? <>
            <button className="btn btn-ghost btn-sm" onClick={() => { logout(); nav('/login') }}>Sign out</button>
            <Link className="btn btn-primary btn-sm" to={home}>Open {role === 'lender' ? 'lender desk' : 'dashboard'}</Link>
          </> : <>
            <Link className="btn btn-ghost btn-sm" to="/login">Sign in</Link>
            <Link className="btn btn-primary btn-sm" to="/signup">Get scored</Link>
          </>}
        </div>
      </header>

      <section className="l-hero">
        <div className="l-hero-copy">
          <span className="chip chip-pos"><Icon name="verified" />Alternative credit scoring · no credit history needed</span>
          <h1>Your everyday habits are your <em>credit score</em>.</h1>
          <p>First job, gig work, or just never took a loan? ALTcredit turns rent, bills, spending and savings into a fair, explainable score, and shows you exactly how to grow it.</p>
          <div className="row wrap" style={{ gap: 12 }}>
            <Link className="btn btn-primary btn-lg" to="/signup">Get your score <Icon name="arrow_forward" /></Link>
            <a className="btn btn-ghost btn-lg" href="#how">See how it works</a>
          </div>
          <small className="l-fine"><Icon name="lock" /> Prototype running on synthetic data · no credit bureau pull</small>
        </div>

        <aside className="l-sample card dark" aria-label="Sample score card">
          <div className="row between"><span className="label" style={{ color: '#94a3b8' }}>Sample profile</span><span className="chip chip-blue">Near-Prime</span></div>
          <div className="row" style={{ gap: 20, margin: '18px 0' }}>
            <ScoreRing value={712} colour="#0284C7" size={104}><Icon name="verified" /></ScoreRing>
            <div><div className="score-num" style={{ color: '#fff' }}>712<small style={{ color: '#94a3b8' }}>/1000</small></div><small style={{ color: '#94a3b8' }}>Estimated default risk 28.8%</small></div>
          </div>
          {[['Lifestyle', 260, 350, '#10b981'], ['Spending', 210, 350, '#f59e0b'], ['Repayment', 400, 570, '#10b981']].map(([n, v, m, c]) => (
            <div key={n} style={{ marginBottom: 10 }}><div className="row between"><small style={{ color: '#cbd5e1' }}>{n}</small><b>{v}</b></div><Bar value={v} max={m} colour={c} /></div>))}
          <div className="l-sample-note"><Icon name="lock_open" /> Unlocks Standard Credit Card</div>
        </aside>
      </section>

      <section className="l-problem">
        <h2>Traditional scores can’t see you.</h2>
        <p>Banks look for past loans and credit cards. If you have none, you’re treated as high risk, however responsible you are. Millions get rejected or pushed toward expensive informal lenders. ALTcredit reads the signals you already generate every month instead.</p>
      </section>

      <section id="how" className="l-section">
        <div className="l-head"><span className="label">How it works</span><h2>From sign-up to score in minutes</h2></div>
        <div className="grid3">
          {STEPS.map((s, i) => (
            <div key={s.title} className="card l-step"><span className="l-num">{i + 1}</span><span className="section-icon"><Icon name={s.icon} /></span><h3>{s.title}</h3><p className="muted">{s.text}</p></div>))}
        </div>
      </section>

      <section id="features" className="l-section">
        <div className="l-head"><span className="label">Features</span><h2>Built to be understood, not just trusted</h2></div>
        <div className="grid3">
          {FEATURES.map((f) => (
            <div key={f.title} className="card l-feature"><span className="section-icon"><Icon name={f.icon} /></span><h3>{f.title}</h3><p className="muted">{f.text}</p></div>))}
        </div>
      </section>

      <section id="score" className="l-section">
        <div className="l-head"><span className="label">The score</span><h2>1000 points, three pillars, no black box</h2>
          <p className="muted">A transparent rule-based framework: every point traces back to something you did.</p></div>
        <div className="grid3">
          {PILLARS.map((p) => (
            <div key={p.name} className="card"><div className="row"><span className="section-icon"><Icon name={p.icon} /></span><h3>{p.name}</h3></div>
              <ul className="checks" style={{ marginTop: 14 }}>{p.items.map((i) => <li key={i}><Icon name="check_circle" />{i}</li>)}</ul></div>))}
        </div>
        <div className="l-bands">
          {BANDS.map((b) => (
            <div key={b.name} className="card l-band" style={{ borderTop: `4px solid ${b.colour}` }}>
              <b style={{ color: b.colour, fontFamily: 'var(--head)', fontSize: 18 }}>{b.name}</b><div className="l-range">{b.range}</div><small className="muted">{b.note}</small></div>))}
        </div>
      </section>

      <section id="lenders" className="l-section">
        <div className="card dark l-lenders">
          <div><span className="label" style={{ color: '#4edea3' }}>For lenders</span><h2>Find creditworthy borrowers the bureaus miss</h2>
            <p style={{ color: '#cbd5e1', margin: '10px 0 18px' }}>Search and filter anonymised candidates by score, default probability, income and debt ratio, review their risk profile, and push loan or card offers in bulk. Names stay hidden until a borrower says yes.</p>
            <Link className="btn btn-primary" to="/login">Lender sign in <Icon name="arrow_forward" /></Link></div>
          <ul className="checks l-lender-list">
            {['Anonymised candidate pool', 'Score, PD, income and DTI filters', 'Bulk offer campaigns', 'Identity revealed only on acceptance'].map((t) => <li key={t}><Icon name="check_circle" />{t}</li>)}
          </ul>
        </div>
      </section>

      <section className="l-cta">
        <h2>Ready to see your score?</h2><p className="muted">Create a profile in about three minutes. It’s free and needs no credit history.</p>
        <Link className="btn btn-primary btn-lg" to="/signup">Create my profile <Icon name="arrow_forward" /></Link>
      </section>

      <footer className="l-foot">
        <Brand />
        <p>ALTcredit is a hackathon prototype that uses synthetic data only. Scores are estimates for demonstration, not an official credit bureau score or a lending decision. Product offers are indicative and do not guarantee approval.</p>
      </footer>
    </div>
  )
}

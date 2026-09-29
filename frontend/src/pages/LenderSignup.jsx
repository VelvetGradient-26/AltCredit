import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { Brand } from '../components/Layout'
import { Icon } from '../components/ui'

export default function LenderSignup() {
  const { registerLender } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({ company_name: '', username: '', password: '', confirm: '', min_score: 650, max_pd: 35 })
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    if (f.password !== f.confirm) return setErr('Passwords do not match')
    setErr(''); setBusy(true)
    try {
      await registerLender({
        company_name: f.company_name.trim(),
        username: f.username.trim().toLowerCase(),
        password: f.password,
        min_credit_score_requirement: Number(f.min_score),
        max_pd_threshold: Number(f.max_pd) / 100,
      })
      nav('/lender')
    } catch (ex) { setErr(ex.message) } finally { setBusy(false) }
  }

  return (
    <div className="auth">
      <form className="auth-card" onSubmit={submit}>
        <Link to="/" aria-label="ALTcredit home"><Brand /></Link>
        <h1>Register as a lender</h1>
        <p>Set your lending policy once and source pre-qualified, anonymised candidates.</p>
        <label className="field"><span>Institution name</span>
          <input required minLength={2} value={f.company_name} onChange={set('company_name')} placeholder="Acme Finance" /></label>
        <label className="field"><span>Username <small>lowercase letters, numbers, _</small></span>
          <input required pattern="[a-z0-9_]{3,40}" autoComplete="username" value={f.username} onChange={set('username')} placeholder="acmefinance" /></label>
        <label className="field"><span>Password <small>min 8 characters</small></span>
          <input required type="password" minLength={8} autoComplete="new-password" value={f.password} onChange={set('password')} /></label>
        <label className="field"><span>Confirm password</span>
          <input required type="password" autoComplete="new-password" value={f.confirm} onChange={set('confirm')} /></label>
        <label className="field"><span>Minimum ALTcredit score <small>0–1000</small></span>
          <input required type="number" min="0" max="1000" value={f.min_score} onChange={set('min_score')} /></label>
        <label className="field"><span>Maximum default probability <small>%</small></span>
          <input required type="number" min="1" max="100" step="1" value={f.max_pd} onChange={set('max_pd')} /></label>
        {err && <div className="err" role="alert">{err}</div>}
        <button className="btn btn-primary" disabled={busy} style={{ padding: 16, fontSize: 17 }}>{busy ? 'Please wait…' : 'Create lender account'} <Icon name="arrow_forward" /></button>
        <p style={{ fontSize: 14 }}>Already registered? <Link className="link" to="/login">Sign in</Link></p>
      </form>
    </div>
  )
}

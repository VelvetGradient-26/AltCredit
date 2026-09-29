import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { Brand } from '../components/Layout'
import { Icon } from '../components/ui'

const DEMO = { user: { username: 'USR_002', password: 'altcredit-demo', label: 'USR_002 (Near-Prime)' },
  lender: { username: 'primebank', password: 'altcredit-demo', label: 'Prime Bank' } }

export default function SignIn() {
  const { login, role: current, userId } = useAuth()
  const nav = useNavigate()
  const [role, setRole] = useState('user')
  const [f, setF] = useState({ username: '', password: '', remember: true })
  const [show, setShow] = useState(false)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setErr(''); setBusy(true)
    try {
      await login(f.username.trim(), f.password, role, f.remember)
      nav(role === 'lender' ? '/lender' : '/dashboard')
    } catch (ex) { setErr(ex.message) } finally { setBusy(false) }
  }

  return (
    <div className="auth">
      <form className="auth-card" onSubmit={submit}>
        <Link to="/" aria-label="ALTcredit home"><Brand /></Link>
        {current && <div className="su-note" role="status"><Icon name="info" /><span>You're signed in as <b>{current === 'lender' ? 'a lender' : userId}</b>. <Link className="link" to={current === 'lender' ? '/lender' : '/dashboard'}>Continue</Link> or sign in below to switch account.</span></div>}
        <h1>{role === 'lender' ? 'Lender sign in' : 'Welcome back'}</h1>
        <p>Sign in to access your ALTcredit dashboard and live score telemetry.</p>
        <div className="seg" role="tablist">
          <button type="button" className={role === 'user' ? 'on' : ''} onClick={() => setRole('user')}>Borrower</button>
          <button type="button" className={role === 'lender' ? 'on' : ''} onClick={() => setRole('lender')}>Lender</button>
        </div>
        <button type="button" className="preset" onClick={() => setF({ ...f, ...DEMO[role] })}>
          <i className="dot" style={{ background: 'var(--emerald)' }} /><b>DEMO PRESET:</b> {DEMO[role].label}<span className="fill">Fill →</span>
        </button>
        <label className="field"><span>{role === 'lender' ? 'Lender username' : 'User ID or email'}</span>
          <div className="input-icon"><Icon name="mail" /><input required autoComplete="username" value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} placeholder={role === 'lender' ? 'primebank' : 'USR_002'} /></div></label>
        <label className="field"><span>Password</span>
          <div className="input-icon"><Icon name="lock" />
            <input required type={show ? 'text' : 'password'} autoComplete="current-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
            <button type="button" className="icon-btn eye" onClick={() => setShow(!show)} aria-label="Toggle password"><Icon name={show ? 'visibility_off' : 'visibility'} /></button></div></label>
        <label className="row" style={{ fontSize: 14 }}><input type="checkbox" checked={f.remember} onChange={(e) => setF({ ...f, remember: e.target.checked })} /> Remember this device</label>
        {err && <div className="err" role="alert">{err}</div>}
        <button className="btn btn-primary" disabled={busy} style={{ padding: 16, fontSize: 17 }}>{busy ? 'Please wait…' : 'Sign In'} <Icon name="arrow_forward" /></button>
        <p style={{ fontSize: 14 }}>{role === 'user'
          ? <>Don't have an ALTcredit account? <Link className="link" to="/signup">Sign up &amp; get scored</Link></>
          : <>New lending institution? <Link className="link" to="/lender/signup">Register as a lender</Link></>}</p>
      </form>
    </div>
  )
}

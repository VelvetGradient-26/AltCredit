import { useEffect, useState } from 'react'

export const Icon = ({ name, className = '' }) => <span className={`material-symbols-outlined ${className}`} aria-hidden="true">{name}</span>

export const fmt = (n, d = 0) => (n == null ? '–' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: d }))

// Grade colours from the design system; keyed by the backend's risk tier label.
export function tierMeta(label = '') {
  if (label.startsWith('Prime')) return { short: 'Excellent', colour: '#10B981', chip: 'chip-pos' }
  if (label.startsWith('Near')) return { short: 'Good', colour: '#0284C7', chip: 'chip-blue' }
  if (label.startsWith('Sub')) return { short: 'Fair', colour: '#F59E0B', chip: 'chip-warn' }
  return { short: 'High risk', colour: '#EF4444', chip: 'chip-bad' }
}

export function ScoreRing({ value, max = 1000, colour = '#10B981', size = 108, children }) {
  const r = 44, c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(1, value / max))
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" width={size} height={size} role="img" aria-label={`Score ${value} of ${max}`}>
        <circle cx="50" cy="50" r={r} fill="none" stroke="#dce9ff" strokeWidth="9" />
        <circle cx="50" cy="50" r={r} fill="none" stroke={colour} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - pct)} transform="rotate(-90 50 50)" style={{ transition: 'stroke-dashoffset .6s' }} />
      </svg>
      <div className="ring-inner">{children}</div>
    </div>
  )
}

export function Arc({ value, max = 1000, colour = '#10B981' }) {
  const pct = Math.max(0, Math.min(1, value / max))
  const len = Math.PI * 80
  return (
    <svg viewBox="0 0 200 110" className="arc" role="img" aria-label={`Projected score ${value}`}>
      <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="rgba(255,255,255,.12)" strokeWidth="14" strokeLinecap="round" />
      <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke={colour} strokeWidth="14" strokeLinecap="round"
        strokeDasharray={len} strokeDashoffset={len * (1 - pct)} style={{ transition: 'stroke-dashoffset .6s' }} />
    </svg>
  )
}

export function Bar({ value, max, colour = 'var(--emerald)' }) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0
  return <div className="bar"><div style={{ width: `${pct}%`, background: colour }} /></div>
}

export function Spinner({ label = 'Loading…' }) {
  return <div className="state" role="status"><div className="spin" />{label}</div>
}

export function ErrorBox({ error, retry }) {
  return (
    <div className="state error" role="alert">
      <Icon name="error" /> {error?.message || String(error)}
      {retry && <button className="btn btn-ghost" onClick={retry}>Retry</button>}
    </div>
  )
}

// Small data hook: { data, error, loading, reload }
export function useLoad(fn, deps = []) {
  const [st, setSt] = useState({ data: null, error: null, loading: true })
  const [n, setN] = useState(0)
  useEffect(() => {
    let live = true
    setSt((s) => ({ ...s, loading: true, error: null }))
    fn().then((data) => live && setSt({ data, error: null, loading: false }),
      (error) => live && setSt({ data: null, error, loading: false }))
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, n])
  return { ...st, reload: () => setN((x) => x + 1) }
}

export function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    const h = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])
  return (
    <div className="overlay" onClick={onClose}>
      <div className={`modal ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head"><h3>{title}</h3><button className="icon-btn" onClick={onClose} aria-label="Close"><Icon name="close" /></button></div>
        {children}
      </div>
    </div>
  )
}

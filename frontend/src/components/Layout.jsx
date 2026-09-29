import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { Icon } from './ui'

const NAV = [
  { to: '/dashboard', icon: 'dashboard', label: 'Dashboard', end: true },
  { to: '/simulator', icon: 'tune', label: 'What-If Simulator' },
  { to: '/recommendations', icon: 'verified', label: 'Recommendations' },
]

export function Brand() {
  return (
    <div className="brand">
      <span className="brand-mark"><Icon name="trending_up" /></span>
      <span>ALT<b>credit</b></span>
    </div>
  )
}

export default function Layout() {
  const { userId, logout } = useAuth()
  const nav = useNavigate()
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link to="/" aria-label="ALTcredit home" style={{ textDecoration: 'none', color: 'inherit' }}><Brand /></Link>
        <nav>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Icon name={n.icon} />{n.label}
            </NavLink>
          ))}
        </nav>
        <button className="nav-item logout" onClick={() => { logout(); nav('/login') }}><Icon name="logout" />Logout</button>
      </aside>
      <div className="main">
        <header className="topbar">
          <span className="topbar-title">ALTcredit Portal</span>
          <span className="chip chip-blue"><i className="dot" />Prototype Sandbox</span>
          <div className="who">
            <div><strong>{userId}</strong><small>Synthetic applicant</small></div>
            <span className="avatar"><Icon name="person" /></span>
          </div>
        </header>
        <main className="content"><Outlet /></main>
        <nav className="bottom-nav">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => (isActive ? 'active' : '')}>
              <Icon name={n.icon} /><span>{n.label.replace('What-If ', '')}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}

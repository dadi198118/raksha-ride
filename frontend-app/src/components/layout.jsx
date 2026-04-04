import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { Shield, LayoutDashboard, Calculator, FileText, LogOut, Activity } from 'lucide-react'

export default function Layout({ riderId, onLogout }) {
  const navigate = useNavigate()

  const handleLogout = () => {
    onLogout()
    navigate('/register')
  }

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/premium', icon: Calculator, label: 'Premium' },
    { to: '/claims', icon: FileText, label: 'Claims' },
    { to: '/ops', icon: Activity, label: 'Ops Admin' },
  ]

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <nav style={{
        width: 220, minWidth: 220,
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column',
        padding: '24px 16px', gap: 4,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', marginBottom: 24 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'var(--accent-dim)',
            border: '1px solid rgba(0,212,170,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Shield size={18} color="var(--accent)" />
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 16, lineHeight: 1 }}>
              Raksha<span style={{ color: 'var(--accent)' }}>Ride</span>
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Income Protection</div>
          </div>
        </div>

        {/* Nav links */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 12px', borderRadius: 'var(--radius)',
                textDecoration: 'none', fontSize: 14,
                fontWeight: isActive ? 500 : 400,
                color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                background: isActive ? 'var(--accent-dim)' : 'transparent',
                border: isActive ? '1px solid rgba(0,212,170,0.15)' : '1px solid transparent',
                transition: 'var(--transition)',
              })}
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </div>

        <div style={{
          padding: '10px 12px', background: 'var(--surface-2)',
          borderRadius: 'var(--radius)', marginBottom: 8, border: '1px solid var(--border)',
        }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>Rider ID</div>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 14, color: 'var(--accent)' }}>
            #{riderId}
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="btn btn-secondary"
          style={{ fontSize: 13, padding: '9px 12px', justifyContent: 'flex-start' }}
        >
          <LogOut size={14} />
          Sign Out
        </button>
      </nav>

      <main style={{ flex: 1, overflow: 'auto', background: 'var(--bg)', padding: '32px' }}>
        <Outlet />
      </main>
    </div>
  )
}
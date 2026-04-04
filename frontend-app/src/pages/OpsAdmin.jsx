import { useEffect, useState } from 'react'
import { getAlerts, getRiders, triggerDetection, mockDisaster } from '../utils/api'
import {
  Activity, AlertTriangle, Users, Shield, Zap,
  RefreshCw, Database, Cpu, Globe
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts'
import axios from 'axios'

const EVENT_COLORS_MAP = {
  flood: '#3b82f6', curfew: '#ef4444', strike: '#f59e0b',
  extreme_weather: '#a78bfa', epidemic: '#ef4444', war: '#ef4444',
}
const ZONE_OPTIONS = [
  { id: 'HYD_500001', name: 'Hyderabad' },
  { id: 'BLR_560001', name: 'Bengaluru' },
  { id: 'MUM_400001', name: 'Mumbai' },
  { id: 'CHN_600001', name: 'Chennai' },
  { id: 'DEL_110001', name: 'Delhi' },
]
const EVENT_OPTIONS = ['flood', 'curfew', 'strike', 'extreme_weather', 'epidemic']

export default function OpsAdmin() {
  const [alerts, setAlerts] = useState([])
  const [riders, setRiders] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [detecting, setDetecting] = useState(false)
  const [simZone, setSimZone] = useState('HYD_500001')
  const [simEvent, setSimEvent] = useState('flood')
  const [simSeverity, setSimSeverity] = useState(4)
  const [simResult, setSimResult] = useState(null)
  const [simulating, setSimulating] = useState(false)

  const load = async () => {
    try {
      const [alertsRes, ridersRes, healthRes] = await Promise.all([
        getAlerts(false),
        getRiders(),
        axios.get('/health'),
      ])
      setAlerts(alertsRes.data)
      setRiders(ridersRes.data)
      setHealth(healthRes.data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleDetect = async () => {
    setDetecting(true)
    try { await triggerDetection(); await load() }
    finally { setDetecting(false) }
  }

  const handleSimulate = async () => {
    setSimulating(true)
    setSimResult(null)
    try {
      const res = await mockDisaster(simZone, simEvent, simSeverity)
      setSimResult(res.data)
      await load()
    } catch (e) { setSimResult({ error: e.message }) }
    finally { setSimulating(false) }
  }

  // Derived stats
  const activeAlerts = alerts.filter(a => a.is_active)
  const resolvedAlerts = alerts.filter(a => !a.is_active)
  const activePolicies = riders.filter(r => r.policy_active).length
  const tierDist = [
    { name: 'Tier 1', value: riders.filter(r => r.city_tier === 1).length },
    { name: 'Tier 2', value: riders.filter(r => r.city_tier === 2).length },
    { name: 'Tier 3', value: riders.filter(r => r.city_tier === 3).length },
  ]
  const platformDist = Object.entries(
    riders.reduce((acc, r) => {
      acc[r.platform] = (acc[r.platform] || 0) + 1; return acc
    }, {})
  ).map(([name, value]) => ({ name, value }))

  const eventTypeDist = Object.entries(
    alerts.reduce((acc, a) => {
      acc[a.event_type] = (acc[a.event_type] || 0) + 1; return acc
    }, {})
  ).map(([name, value]) => ({ name, value }))

  const PIE_COLORS = ['var(--accent)', '#3b82f6', '#f59e0b', '#a78bfa', '#ef4444']

  if (loading) return <div className="loading-center"><span className="spinner" /></div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div className="fade-up" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 26, marginBottom: 6 }}>
            Operations Dashboard
          </h1>
          <div style={{ color: 'var(--text-secondary)', fontSize: 14, display: 'flex', gap: 12 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="live-dot" />
              System live
            </span>
            <span>·</span>
            <span>Scheduler: {health?.scheduler === 'running' ? '✅ Running' : '⚠ Stopped'}</span>
            <span>·</span>
            <span>Weather API: {health?.weather_api === 'connected' ? '✅ Open-Meteo' : '⚠ Fallback'}</span>
          </div>
        </div>
        <button
          className="btn btn-secondary"
          onClick={handleDetect}
          disabled={detecting}
          style={{ fontSize: 13 }}
        >
          {detecting
            ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Running…</>
            : <><RefreshCw size={14} /> Run AI Detection Cycle</>}
        </button>
      </div>

      {/* KPI row */}
      <div className="grid-4 fade-up-2">
        {[
          { label: 'Total Riders', value: riders.length, icon: Users, color: 'var(--blue)' },
          { label: 'Active Policies', value: activePolicies, icon: Shield, color: 'var(--accent)' },
          { label: 'Active Alerts', value: activeAlerts.length, icon: AlertTriangle, color: activeAlerts.length > 0 ? 'var(--red)' : 'var(--text-muted)' },
          { label: 'Total Alerts (All)', value: alerts.length, icon: Activity, color: 'var(--purple)' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{
              width: 44, height: 44, borderRadius: 12, flexShrink: 0,
              background: `${color}18`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Icon size={20} color={color} />
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 28, lineHeight: 1, color }}>
                {value}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3 }}>{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid-3 fade-up-3">
        {/* Rider tier dist */}
        <div className="card">
          <div className="section-title">Riders by Tier</div>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={tierDist} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60} label={({ name, value }) => `${name}: ${value}`}>
                {tierDist.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Platform dist */}
        <div className="card">
          <div className="section-title">Riders by Platform</div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={platformDist} barSize={28}>
              <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis hide />
              <Tooltip contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {platformDist.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Event type dist */}
        <div className="card">
          <div className="section-title">Alerts by Event Type</div>
          {eventTypeDist.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', paddingTop: 40 }}>
              No alerts recorded yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={eventTypeDist} barSize={24}>
                <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {eventTypeDist.map((d, i) => <Cell key={i} fill={EVENT_COLORS_MAP[d.name] || PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Demo control panel + Alert log side by side */}
      <div className="grid-2 fade-up-4">
        {/* Disaster simulator — for demo/judges */}
        <div className="card" style={{ border: '1px solid rgba(239,68,68,0.2)', background: 'rgba(239,68,68,0.03)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <Zap size={16} color="var(--red)" />
            <div className="section-title" style={{ margin: 0, color: 'var(--red)' }}>Demo Disaster Simulator</div>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 20, lineHeight: 1.6 }}>
            Inject a mock disaster alert into a zone. The backend will immediately run
            eligibility checks for all riders in that zone and create zero-touch claim payouts.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="form-group">
              <label className="form-label">Target Zone</label>
              <select className="form-input" value={simZone} onChange={e => setSimZone(e.target.value)}>
                {ZONE_OPTIONS.map(z => (
                  <option key={z.id} value={z.id}>{z.name} ({z.id})</option>
                ))}
              </select>
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Event Type</label>
                <select className="form-input" value={simEvent} onChange={e => setSimEvent(e.target.value)}>
                  {EVENT_OPTIONS.map(e => (
                    <option key={e} value={e}>{e.replace('_', ' ')}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Severity (1–5)</label>
                <input
                  type="number" min={1} max={5} className="form-input"
                  value={simSeverity}
                  onChange={e => setSimSeverity(Number(e.target.value))}
                />
              </div>
            </div>

            <button
              className="btn btn-danger btn-full"
              onClick={handleSimulate}
              disabled={simulating}
              style={{ marginTop: 4 }}
            >
              {simulating
                ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Processing…</>
                : <><Zap size={14} /> Trigger Disaster & Auto-Process Claims</>}
            </button>
          </div>

          {simResult && !simResult.error && (
            <div style={{
              marginTop: 16, padding: '14px 16px',
              background: 'var(--accent-dim)', borderRadius: 'var(--radius)',
              border: '1px solid rgba(0,212,170,0.2)',
            }}>
              <div style={{ fontWeight: 600, color: 'var(--accent)', marginBottom: 8 }}>
                ✅ Alert #{simResult.alert?.id} fired — {simResult.riders_processed} rider(s) processed
              </div>
              {simResult.claims_created?.map((c, i) => (
                <div key={i} style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
                  → {c.rider_name}: ₹{c.daily_payout}/day · fraud score {c.fraud_score} · <strong>{c.status}</strong>
                </div>
              ))}
              {simResult.claims_created?.length === 0 && (
                <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                  No new claims created (riders may already have active claims for this zone).
                </div>
              )}
            </div>
          )}

          {simResult?.error && (
            <div style={{ marginTop: 12, color: 'var(--red)', fontSize: 13 }}>
              Error: {simResult.error}
            </div>
          )}
        </div>

        {/* Active alerts log */}
        <div className="card">
          <div className="section-title">All Disruption Alerts</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 440, overflowY: 'auto' }}>
            {alerts.length === 0 && (
              <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: '30px 0' }}>
                No alerts yet — run the detection cycle or simulate a disaster
              </div>
            )}
            {alerts.map(alert => (
              <div key={alert.id} style={{
                padding: '12px 14px',
                background: 'var(--surface-2)',
                borderRadius: 'var(--radius)',
                border: `1px solid ${alert.is_active ? 'rgba(239,68,68,0.2)' : 'var(--border)'}`,
                display: 'flex', gap: 12, alignItems: 'flex-start',
              }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%', marginTop: 5, flexShrink: 0,
                  background: alert.is_active ? 'var(--red)' : 'var(--text-muted)',
                  boxShadow: alert.is_active ? '0 0 6px var(--red)' : 'none',
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 3 }}>
                    <span style={{
                      fontWeight: 600, fontSize: 14, textTransform: 'capitalize',
                      color: EVENT_COLORS_MAP[alert.event_type] || 'var(--text-primary)'
                    }}>
                      {alert.event_type?.replace('_', ' ')}
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      Zone {alert.zone_id}
                    </span>
                    <span className={`badge ${alert.is_active ? 'badge-red' : 'badge-purple'}`} style={{ fontSize: 10, padding: '2px 8px' }}>
                      {alert.is_active ? 'Active' : 'Resolved'}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                    <span>Sev {alert.severity}/5</span>
                    <span>·</span>
                    <span>{Math.round(alert.confidence * 100)}% conf</span>
                    <span>·</span>
                    <span>{alert.sources_confirmed?.join(', ')}</span>
                  </div>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>
                  #{alert.id}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Rider table */}
      <div className="card fade-up" style={{ marginBottom: 8 }}>
        <div className="section-title">Registered Riders</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr>
                {['ID', 'Name', 'City', 'Platform', 'Tier', 'Policy', 'Weeks', 'Days Claimed', 'Loyalty'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left', padding: '8px 12px',
                    color: 'var(--text-muted)', fontSize: 12,
                    fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em',
                    borderBottom: '1px solid var(--border)',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {riders.map(r => (
                <tr key={r.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>#{r.id}</td>
                  <td style={{ padding: '10px 12px', fontWeight: 500 }}>{r.name}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{r.city}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{r.platform}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span className={`badge ${r.city_tier === 1 ? 'badge-green' : r.city_tier === 2 ? 'badge-blue' : 'badge-purple'}`}
                      style={{ fontSize: 11 }}>
                      T{r.city_tier}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <span className={`badge ${r.policy_active ? 'badge-green' : 'badge-amber'}`} style={{ fontSize: 11 }}>
                      {r.policy_active ? 'Active' : 'Pending'}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--font-display)', fontWeight: 700 }}>
                    {r.weeks_contributed}
                  </td>
                  <td style={{ padding: '10px 12px', color: r.total_days_claimed > 20 ? 'var(--red)' : 'var(--text-primary)' }}>
                    {r.total_days_claimed}/30
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    {r.loyalty_discount
                      ? <span className="badge badge-purple" style={{ fontSize: 11 }}>15% off</span>
                      : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import {
  Shield, Zap, AlertTriangle, TrendingUp,
  CheckCircle, Clock, XCircle, RefreshCw,
  CloudRain, Users, Award, Calendar
} from 'lucide-react'
import { getRiderDashboard, triggerDetection, mockDisaster } from '../utils/api'

const EVENT_ICONS = {
  flood: '🌊', curfew: '🚫', strike: '✊', extreme_weather: '⛈️',
  epidemic: '🦠', war: '⚔️'
}
const EVENT_COLORS = {
  flood: 'var(--blue)', curfew: 'var(--red)',
  strike: 'var(--amber)', extreme_weather: 'var(--purple)',
  epidemic: 'var(--red)', war: 'var(--red)'
}
const SEV_COLORS = ['', '#4ade80', '#facc15', 'var(--amber)', '#f97316', 'var(--red)']

export default function Dashboard({ riderId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [detecting, setDetecting] = useState(false)
  const [simulating, setSimulating] = useState(false)

  const load = async () => {
    try {
      const res = await getRiderDashboard(riderId)
      setData(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [riderId])

  const handleDetect = async () => {
    setDetecting(true)
    try {
      await triggerDetection()
      await load()
    } finally {
      setDetecting(false)
    }
  }

  const handleMockDisaster = async () => {
    if (!data) return
    setSimulating(true)
    try {
      await mockDisaster(data.rider.zone_id, 'flood', 4)
      await load()
    } finally {
      setSimulating(false)
    }
  }

  if (loading) return (
    <div className="loading-center">
      <span className="spinner" />
      <span style={{ color: 'var(--text-secondary)' }}>Loading dashboard…</span>
    </div>
  )
  if (!data) return <div style={{ color: 'var(--red)' }}>Failed to load dashboard.</div>

  const { rider, policy, contributions, active_claims, zone_alerts } = data
  const pctCap = Math.round((policy.days_used / 30) * 100)
  const hasActiveAlert = zone_alerts.length > 0
  const hasActiveClaim = active_claims.length > 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div className="fade-up" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 26, marginBottom: 4 }}>
            Hey, {rider.name.split(' ')[0]} 👋
          </h1>
          <div style={{ color: 'var(--text-secondary)', fontSize: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="live-dot" />
            {rider.city} · {rider.platform} · Zone {rider.zone_id}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-secondary" onClick={handleDetect} disabled={detecting} style={{ fontSize: 13 }}>
            {detecting ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <RefreshCw size={14} />}
            Run AI Detection
          </button>
          <button className="btn btn-danger" onClick={handleMockDisaster} disabled={simulating} style={{ fontSize: 13 }}>
            {simulating ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <Zap size={14} />}
            Simulate Disaster
          </button>
        </div>
      </div>

      {/* Active claim banner */}
      {hasActiveClaim && (
        <div className="fade-up" style={{
          background: 'rgba(0,212,170,0.08)',
          border: '1px solid rgba(0,212,170,0.3)',
          borderRadius: 'var(--radius-lg)',
          padding: '20px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{
              width: 44, height: 44, borderRadius: '50%',
              background: 'var(--accent-dim)', border: '2px solid var(--accent)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Shield size={20} color="var(--accent)" />
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, color: 'var(--accent)' }}>
                You are covered. Payout is being processed.
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 3 }}>
                ₹{active_claims[0].daily_amount}/day · {active_claims[0].days_paid} days paid so far · ₹{active_claims[0].total_paid} total disbursed
              </div>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 24, color: 'var(--accent)' }}>
              ₹{active_claims[0].total_paid.toLocaleString()}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>total received</div>
          </div>
        </div>
      )}

      {/* Active alert banner */}
      {hasActiveAlert && !hasActiveClaim && zone_alerts.map(alert => (
        <div key={alert.alert_id} style={{
          background: 'rgba(239,68,68,0.07)',
          border: '1px solid rgba(239,68,68,0.25)',
          borderRadius: 'var(--radius-lg)',
          padding: '16px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: 14,
        }}>
          <span style={{ fontSize: 24 }}>{EVENT_ICONS[alert.event_type] || '⚠️'}</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: 15, textTransform: 'capitalize', marginBottom: 2 }}>
              {alert.event_type.replace('_', ' ')} alert active in your zone
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Confidence: {Math.round(alert.confidence * 100)}% · Sources: {alert.sources.join(', ')} · Est. {alert.estimated_days} day(s)
            </div>
          </div>
          <div className="badge badge-red">
            Sev {alert.severity}/5
          </div>
        </div>
      ))}

      {/* Key stats row */}
      <div className="grid-4 fade-up-2">
        {[
          {
            value: policy.status === 'active' ? 'Active' : 'Pending',
            label: 'Policy Status',
            icon: policy.status === 'active' ? CheckCircle : Clock,
            color: policy.status === 'active' ? 'var(--accent)' : 'var(--amber)',
            sub: policy.status === 'active' ? '✓ Fully covered' : `${policy.weeks_to_activation} weeks to activate`
          },
          {
            value: `₹${contributions.avg_weekly}`,
            label: 'Avg Weekly Contribution',
            icon: TrendingUp,
            color: 'var(--blue)',
            sub: `Last week: ₹${contributions.last_week}`
          },
          {
            value: `${policy.days_remaining} days`,
            label: 'Coverage Remaining',
            icon: Calendar,
            color: policy.days_remaining < 10 ? 'var(--red)' : 'var(--accent)',
            sub: `${policy.days_used} of 30 days used`
          },
          {
            value: rider.no_claim_streak,
            label: 'Weeks No Claim',
            icon: Award,
            color: 'var(--purple)',
            sub: rider.loyalty_discount ? '✓ Loyalty discount active' : `${Math.max(0, 24 - rider.no_claim_streak)} weeks to discount`
          }
        ].map(({ value, label, icon: Icon, color, sub }) => (
          <div key={label} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div className="stat-value" style={{ color }}>{value}</div>
                <div className="stat-label">{label}</div>
              </div>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: `${color}18`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Icon size={16} color={color} />
              </div>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{sub}</div>
          </div>
        ))}
      </div>

      {/* Coverage cap progress */}
      <div className="card fade-up-3">
        <div className="section-title">6-Month Coverage Cap</div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
          <span style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
            {policy.days_used} days used of 30-day period cap
          </span>
          <span style={{ fontSize: 14, fontWeight: 600 }}>{pctCap}%</span>
        </div>
        <div className="progress-bar-track">
          <div className="progress-bar-fill" style={{
            width: `${pctCap}%`,
            background: pctCap > 80 ? 'linear-gradient(90deg, var(--amber), var(--red))' : undefined
          }} />
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
          Max 14 days per event · {policy.days_remaining} days remaining this period
        </div>
      </div>

      {/* Zone alerts + Claim history side by side */}
      <div className="grid-2 fade-up-4">
        {/* Zone alerts */}
        <div className="card">
          <div className="section-title">Zone Disruption Alerts</div>
          {zone_alerts.length === 0 ? (
            <div style={{
              textAlign: 'center', padding: '30px 0',
              color: 'var(--text-muted)', fontSize: 13
            }}>
              <CheckCircle size={32} color="var(--accent)" style={{ marginBottom: 8, display: 'block', margin: '0 auto 8px' }} />
              No active alerts in your zone
            </div>
          ) : zone_alerts.map(alert => (
            <div key={alert.alert_id} style={{
              display: 'flex', gap: 12, padding: '12px 0',
              borderBottom: '1px solid var(--border)'
            }}>
              <span style={{ fontSize: 22 }}>{EVENT_ICONS[alert.event_type] || '⚠️'}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500, textTransform: 'capitalize', marginBottom: 3 }}>
                  {alert.event_type.replace('_', ' ')}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {Math.round(alert.confidence * 100)}% confidence · {alert.sources.join(', ')}
                </div>
              </div>
              <div className={`badge badge-${alert.severity >= 4 ? 'red' : alert.severity >= 3 ? 'amber' : 'blue'}`}>
                Sev {alert.severity}
              </div>
            </div>
          ))}
        </div>

        {/* Recent payouts */}
        <div className="card">
          <div className="section-title">Recent Payouts</div>
          {active_claims.length === 0 ? (
            <div style={{
              textAlign: 'center', padding: '30px 0',
              color: 'var(--text-muted)', fontSize: 13
            }}>
              <Shield size={32} color="var(--text-muted)" style={{ display: 'block', margin: '0 auto 8px' }} />
              No payouts yet — your coverage is standing by
            </div>
          ) : active_claims.map(claim => (
            <div key={claim.claim_id} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '12px 0', borderBottom: '1px solid var(--border)'
            }}>
              <div>
                <div style={{ fontWeight: 500, marginBottom: 2 }}>
                  Claim #{claim.claim_id}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {claim.days_paid} days · ₹{claim.daily_amount}/day
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--accent)' }}>
                  ₹{claim.total_paid.toLocaleString()}
                </div>
                <span className={`badge badge-${claim.status === 'active' ? 'green' : 'amber'}`}
                  style={{ fontSize: 11 }}>
                  {claim.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Loyalty benefit */}
      {rider.loyalty_discount && (
        <div style={{
          background: 'rgba(167,139,250,0.07)',
          border: '1px solid rgba(167,139,250,0.2)',
          borderRadius: 'var(--radius-lg)',
          padding: '16px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: 14,
        }}>
          <Award size={20} color="var(--purple)" />
          <div>
            <div style={{ fontWeight: 600, color: 'var(--purple)', marginBottom: 2 }}>
              Loyalty Discount Active — 15% off contributions
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              You protected yourself for 6 months with no claims. You now pay less for the same protection.
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

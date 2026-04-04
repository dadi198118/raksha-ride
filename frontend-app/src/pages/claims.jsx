import { useEffect, useState } from 'react'
import { getRiderClaims, getAlerts, checkEligibility, getRider } from '../utils/api'
import { Shield, CheckCircle, Clock, XCircle, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'

const STATUS_CONFIG = {
  active: { label: 'Active — Payout Running', badge: 'badge-green', icon: CheckCircle, color: 'var(--accent)' },
  processing: { label: 'Processing', badge: 'badge-blue', icon: Clock, color: 'var(--blue)' },
  completed: { label: 'Completed', badge: 'badge-purple', icon: CheckCircle, color: 'var(--purple)' },
  held: { label: '24h Review', badge: 'badge-amber', icon: Clock, color: 'var(--amber)' },
  rejected: { label: 'Rejected', badge: 'badge-red', icon: XCircle, color: 'var(--red)' },
}

const EVENT_ICONS = {
  flood: '🌊', curfew: '🚫', strike: '✊',
  extreme_weather: '⛈️', epidemic: '🦠', war: '⚔️'
}

export default function Claims({ riderId }) {
  const [claims, setClaims] = useState([])
  const [alerts, setAlerts] = useState([])
  const [rider, setRider] = useState(null)
  const [loading, setLoading] = useState(true)
  const [expandedAlert, setExpandedAlert] = useState(null)
  const [eligibilityResults, setEligibilityResults] = useState({})
  const [checkingId, setCheckingId] = useState(null)

  useEffect(() => {
    Promise.all([
      getRiderClaims(riderId),
      getAlerts(true),
      getRider(riderId)
    ]).then(([claimsRes, alertsRes, riderRes]) => {
      setClaims(claimsRes.data)
      setAlerts(alertsRes.data)
      setRider(riderRes.data)
    }).finally(() => setLoading(false))
  }, [riderId])

  const handleCheckEligibility = async (alertId) => {
    setCheckingId(alertId)
    try {
      const res = await checkEligibility(riderId, alertId)
      setEligibilityResults(prev => ({ ...prev, [alertId]: res.data }))
      setExpandedAlert(alertId)
    } catch (e) {
      console.error(e)
    } finally {
      setCheckingId(null)
    }
  }

  const formatDate = (d) => new Date(d).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  })

  if (loading) return <div className="loading-center"><span className="spinner" /></div>

  const hasClaims = claims.length > 0
  const hasActiveAlerts = alerts.length > 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 860 }}>
      {/* Header */}
      <div className="fade-up">
        <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 26, marginBottom: 6 }}>
          Claims
        </h1>
        <div style={{ color: 'var(--text-secondary)', fontSize: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Shield size={14} />
          Zero-touch claims — you never need to file anything. The AI detects disruptions and processes payouts automatically.
        </div>
      </div>

      {/* How it works */}
      <div className="card fade-up-2" style={{
        background: 'rgba(0,212,170,0.04)',
        border: '1px solid rgba(0,212,170,0.15)',
      }}>
        <div className="section-title">How Zero-Touch Claims Work</div>
        <div style={{ display: 'flex', gap: 0 }}>
          {[
            { step: '01', title: 'AI Detects', desc: 'Disruption detection engine monitors news, weather & govt feeds 24/7' },
            { step: '02', title: 'Auto Verified', desc: 'Your GPS, order status & zone data verified automatically in seconds' },
            { step: '03', title: 'Payout Sent', desc: 'Money transferred to your UPI — no claim form, no documents, no waiting' },
          ].map(({ step, title, desc }, i) => (
            <div key={step} style={{ flex: 1, padding: '0 16px', borderRight: i < 2 ? '1px solid var(--border)' : 'none' }}>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 28, color: 'var(--accent)', opacity: 0.3, marginBottom: 6 }}>
                {step}
              </div>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{title}</div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Active zone alerts — check eligibility */}
      <div className="fade-up-3">
        <div className="section-title">Active Zone Alerts</div>
        {!hasActiveAlerts ? (
          <div className="card" style={{ textAlign: 'center', padding: '40px 24px' }}>
            <CheckCircle size={36} color="var(--accent)" style={{ margin: '0 auto 12px', display: 'block' }} />
            <div style={{ fontWeight: 600, marginBottom: 6 }}>No active disruptions</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Your zone is clear. Your coverage is standing by.
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {alerts.map(alert => {
              const eligibility = eligibilityResults[alert.id]
              const isExpanded = expandedAlert === alert.id

              return (
                <div key={alert.id} className="card" style={{ padding: 0, overflow: 'hidden' }}>
                  {/* Alert header */}
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 16,
                    padding: '18px 20px',
                    background: 'rgba(239,68,68,0.04)',
                    borderBottom: isExpanded ? '1px solid var(--border)' : 'none',
                  }}>
                    <span style={{ fontSize: 28 }}>{EVENT_ICONS[alert.event_type] || '⚠️'}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: 15, textTransform: 'capitalize', marginBottom: 3 }}>
                        {alert.event_type.replace('_', ' ')} — Zone {alert.zone_id}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', gap: 12 }}>
                        <span>Confidence: {Math.round(alert.confidence * 100)}%</span>
                        <span>Sources: {alert.sources_confirmed?.join(', ')}</span>
                        <span>Est. {alert.estimated_duration_days} day(s)</span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <span className={`badge badge-${alert.severity >= 4 ? 'red' : 'amber'}`}>
                        Severity {alert.severity}/5
                      </span>
                      <button
                        className="btn btn-primary"
                        style={{ fontSize: 12, padding: '8px 16px' }}
                        onClick={() => handleCheckEligibility(alert.id)}
                        disabled={checkingId === alert.id}
                      >
                        {checkingId === alert.id
                          ? <><span className="spinner" style={{ width: 12, height: 12 }} /> Checking…</>
                          : 'Check My Eligibility'}
                      </button>
                      {eligibility && (
                        <button
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                          onClick={() => setExpandedAlert(isExpanded ? null : alert.id)}
                        >
                          {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Eligibility result */}
                  {eligibility && isExpanded && (
                    <div style={{ padding: '20px' }}>
                      {eligibility.eligible ? (
                        <div>
                          <div style={{
                            display: 'flex', alignItems: 'center', gap: 12,
                            padding: '16px', background: 'var(--accent-dim)',
                            borderRadius: 'var(--radius)', marginBottom: 16,
                            border: '1px solid rgba(0,212,170,0.2)'
                          }}>
                            <CheckCircle size={20} color="var(--accent)" />
                            <div>
                              <div style={{ fontWeight: 600, color: 'var(--accent)' }}>
                                Eligible — Payout {eligibility.fraud_decision === 'auto_approved' ? 'Auto-Approved' : 'Under Review'}
                              </div>
                              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
                                {eligibility.fraud_decision === 'auto_approved'
                                  ? 'Payment will be transferred to your UPI automatically.'
                                  : '24-hour silent review in progress. Payout will follow shortly.'}
                              </div>
                            </div>
                          </div>
                          <div className="grid-3">
                            {[
                              ['Daily Payout', `₹${eligibility.daily_payout}`],
                              ['Est. Total (14d)', `₹${eligibility.estimated_total_payout?.toFixed(0)}`],
                              ['Days Remaining', `${eligibility.days_remaining_period} of 30`],
                            ].map(([k, v]) => (
                              <div key={k} style={{ textAlign: 'center', padding: '12px', background: 'var(--surface-2)', borderRadius: 'var(--radius)' }}>
                                <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 20, color: 'var(--accent)' }}>{v}</div>
                                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 3 }}>{k}</div>
                              </div>
                            ))}
                          </div>
                          <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 8 }}>
                            <span>Fraud score: {eligibility.fraud_score} / 100</span>
                            <span>·</span>
                            <span style={{ textTransform: 'capitalize' }}>{eligibility.fraud_decision.replace('_', ' ')}</span>
                          </div>
                        </div>
                      ) : (
                        <div>
                          <div style={{
                            display: 'flex', alignItems: 'flex-start', gap: 12,
                            padding: '16px', background: 'var(--red-dim)',
                            borderRadius: 'var(--radius)', marginBottom: 16,
                            border: '1px solid rgba(239,68,68,0.2)'
                          }}>
                            <XCircle size={20} color="var(--red)" style={{ flexShrink: 0, marginTop: 1 }} />
                            <div>
                              <div style={{ fontWeight: 600, color: 'var(--red)', marginBottom: 8 }}>
                                Not Eligible at This Time
                              </div>
                              {eligibility.rejection_reasons.map((r, i) => (
                                <div key={i} style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 4, display: 'flex', gap: 6 }}>
                                  <span style={{ color: 'var(--red)' }}>→</span> {r}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Claim history */}
      <div className="fade-up-4">
        <div className="section-title">Payout History</div>
        {!hasClaims ? (
          <div className="card" style={{ textAlign: 'center', padding: '40px 24px' }}>
            <Shield size={36} color="var(--text-muted)" style={{ margin: '0 auto 12px', display: 'block' }} />
            <div style={{ fontWeight: 600, marginBottom: 6 }}>No payouts yet</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              When a disruption is detected in your zone and you're eligible,<br />
              payouts will appear here automatically.
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {claims.map(claim => {
              const sc = STATUS_CONFIG[claim.status] || STATUS_CONFIG.processing
              const Icon = sc.icon

              return (
                <div key={claim.claim_id} className="card" style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: 12, flexShrink: 0,
                    background: `${sc.color}18`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                  }}>
                    <Icon size={20} color={sc.color} />
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                      <span style={{ fontSize: 18 }}>{EVENT_ICONS[claim.event_type] || '⚠️'}</span>
                      <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                        {claim.event_type?.replace('_', ' ')} — Claim #{claim.claim_id}
                      </span>
                      <span className={`badge ${sc.badge}`} style={{ fontSize: 11 }}>
                        {sc.label}
                      </span>
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                      {formatDate(claim.created_at)} · Zone {claim.zone_id} · {claim.days_paid} days paid
                    </div>
                    {claim.rejection_reason && (
                      <div style={{ fontSize: 12, color: 'var(--red)', marginTop: 4 }}>
                        {claim.rejection_reason}
                      </div>
                    )}
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 24, color: sc.color }}>
                      ₹{claim.total_paid.toLocaleString()}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      ₹{claim.daily_amount}/day
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

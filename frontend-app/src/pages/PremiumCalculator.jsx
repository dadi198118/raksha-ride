import { useEffect, useState } from 'react'
import { previewPricing, getRider } from '../utils/api'
import { Calculator, TrendingUp, CloudRain, MapPin, Zap, Info } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const WEATHER_LABELS = { none: '✅ Clear', yellow: '🟡 Yellow Alert', orange: '🟠 Orange Alert', red: '🔴 Red Alert' }
const WEATHER_COLOR = { none: 'var(--accent)', yellow: '#facc15', orange: 'var(--amber)', red: 'var(--red)' }

export default function PremiumCalculator({ riderId }) {
  const [rider, setRider] = useState(null)
  const [deliveries, setDeliveries] = useState(90)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getRider(riderId).then(r => setRider(r.data))
  }, [riderId])

  useEffect(() => {
    if (!rider) return
    const t = setTimeout(() => fetchPreview(), 300)
    return () => clearTimeout(t)
  }, [deliveries, rider])

  const fetchPreview = async () => {
    if (!rider) return
    setLoading(true)
    try {
      const res = await previewPricing(riderId, deliveries)
      setResult(res.data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  if (!rider) return (
    <div className="loading-center"><span className="spinner" /></div>
  )

  const bd = result?.breakdown
  const weather = result?.weather
  const payout = result?.payout_estimate_if_claimed

  const chartData = bd ? [
    { name: 'Base', value: bd.base_contribution, color: 'var(--blue)' },
    { name: 'Zone Risk', value: Math.abs(bd.zone_risk_adjustment), color: bd.zone_risk_adjustment >= 0 ? 'var(--amber)' : 'var(--accent)' },
    { name: 'Weather', value: Math.abs(bd.weather_adjustment), color: 'var(--purple)' },
    { name: 'Performance', value: Math.abs(bd.performance_adjustment), color: bd.performance_adjustment >= 0 ? 'var(--red)' : 'var(--accent)' },
  ] : []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 900 }}>
      {/* Header */}
      <div className="fade-up">
        <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 26, marginBottom: 6 }}>
          Dynamic Premium Calculator
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          See exactly how your weekly contribution is calculated — full transparency.
        </p>
      </div>

      {/* Delivery slider */}
      <div className="card fade-up-2">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <div className="section-title" style={{ marginBottom: 4 }}>This Week's Deliveries</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Drag to simulate different delivery counts
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 36, color: 'var(--accent)', lineHeight: 1 }}>
              {deliveries}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>deliveries</div>
          </div>
        </div>

        <input
          type="range"
          min={20}
          max={160}
          value={deliveries}
          onChange={e => setDeliveries(Number(e.target.value))}
          style={{
            width: '100%',
            appearance: 'none',
            height: 6,
            borderRadius: 100,
            background: `linear-gradient(90deg, var(--accent) ${((deliveries-20)/140)*100}%, var(--surface-3) ${((deliveries-20)/140)*100}%)`,
            outline: 'none',
            cursor: 'pointer',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
          <span>20 (slow week)</span>
          <span>90 (average)</span>
          <span>160 (busy week)</span>
        </div>
      </div>

      {/* Result */}
      {loading && (
        <div className="loading-center" style={{ height: 80 }}>
          <span className="spinner" />
          <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Calculating…</span>
        </div>
      )}

      {result && !loading && (
        <>
          {/* Contribution amount hero */}
          <div className="card fade-up" style={{
            background: 'linear-gradient(135deg, rgba(0,212,170,0.06) 0%, rgba(59,130,246,0.06) 100%)',
            border: '1px solid rgba(0,212,170,0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24
          }}>
            <div>
              <div className="section-title">This Week's Contribution</div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 48, color: 'var(--accent)', lineHeight: 1 }}>
                ₹{result.contribution_amount}
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 8 }}>
                {result.contribution_pct_of_earning}% of ₹{result.weekly_earning_estimate.toLocaleString()} estimated earnings
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>If you claim</div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 28, color: 'var(--text-primary)' }}>
                ₹{payout?.daily_payout}/day
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>for up to 14 days</div>
            </div>
          </div>

          {/* Breakdown grid */}
          <div className="grid-2 fade-up-2">
            {/* Left: factor breakdown */}
            <div className="card">
              <div className="section-title">Contribution Breakdown</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                {[
                  {
                    label: 'Base contribution',
                    value: `₹${bd.base_contribution.toFixed(2)}`,
                    sub: `${deliveries} deliveries × ₹${bd.base_rate_per_delivery}`,
                    color: 'var(--blue)', sign: '='
                  },
                  {
                    label: 'Zone risk adjustment',
                    value: `${bd.zone_risk_adjustment >= 0 ? '+' : ''}₹${bd.zone_risk_adjustment.toFixed(2)}`,
                    sub: `Zone risk score: ${bd.zone_risk_score} (${bd.zone_risk_score > 0.6 ? 'high risk zone' : 'safe zone'})`,
                    color: bd.zone_risk_adjustment >= 0 ? 'var(--amber)' : 'var(--accent)', sign: bd.zone_risk_adjustment >= 0 ? '+' : '−'
                  },
                  {
                    label: 'Weather adjustment',
                    value: `+₹${bd.weather_adjustment.toFixed(2)}`,
                    sub: `Weather severity: ${(bd.weather_severity_score * 100).toFixed(0)}%`,
                    color: 'var(--purple)', sign: '+'
                  },
                  {
                    label: 'Performance adjustment',
                    value: `${bd.performance_adjustment >= 0 ? '+' : ''}₹${bd.performance_adjustment.toFixed(2)}`,
                    sub: `Performance ratio: ${bd.performance_ratio}×`,
                    color: bd.performance_adjustment >= 0 ? 'var(--red)' : 'var(--accent)', sign: bd.performance_adjustment >= 0 ? '+' : '−'
                  },
                  ...(bd.loyalty_discount_applied ? [{
                    label: 'Loyalty discount (15%)',
                    value: `₹${bd.loyalty_adjustment.toFixed(2)}`,
                    sub: '6-month no-claim reward',
                    color: 'var(--purple)', sign: '−'
                  }] : []),
                ].map(({ label, value, sub, color, sign }, i, arr) => (
                  <div key={label} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px 0',
                    borderBottom: i < arr.length - 1 ? '1px solid var(--border)' : 'none',
                    gap: 12
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 2 }}>{label}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{sub}</div>
                    </div>
                    <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, color }}>
                      {value}
                    </div>
                  </div>
                ))}
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '14px 0', borderTop: '2px solid var(--accent)',
                  marginTop: 4
                }}>
                  <div style={{ fontWeight: 600 }}>Total this week</div>
                  <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 20, color: 'var(--accent)' }}>
                    ₹{result.contribution_amount}
                  </div>
                </div>
              </div>
            </div>

            {/* Right: weather + payout info */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Weather card */}
              <div className="card" style={{ flex: 1 }}>
                <div className="section-title">Live Weather — {rider.city}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
                  <div style={{
                    fontSize: 36,
                    width: 56, height: 56, borderRadius: 14,
                    background: `${WEATHER_COLOR[weather?.alert_level || 'none']}18`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {weather?.alert_level === 'red' ? '⛈️' :
                     weather?.alert_level === 'orange' ? '🌧️' :
                     weather?.alert_level === 'yellow' ? '🌦️' : '☀️'}
                  </div>
                  <div>
                    <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, marginBottom: 3 }}>
                      {WEATHER_LABELS[weather?.alert_level || 'none']}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                      Severity: {((weather?.severity_score || 0) * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
                {[
                  ['Precipitation', `${weather?.precipitation_mm || 0} mm`],
                  ['Wind Speed', `${weather?.windspeed_kmh || 0} km/h`],
                  ['Max Hourly Rain', `${weather?.max_hourly_precip || 0} mm`],
                  ['Source', weather?.source || 'Open-Meteo'],
                ].map(([k, v]) => (
                  <div key={k} style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 13
                  }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
                    <span style={{ fontWeight: 500 }}>{v}</span>
                  </div>
                ))}
              </div>

              {/* Payout estimate */}
              <div className="card" style={{
                background: 'rgba(0,212,170,0.04)',
                border: '1px solid rgba(0,212,170,0.15)',
              }}>
                <div className="section-title">Payout If Claimed</div>
                <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 32, color: 'var(--accent)', marginBottom: 4 }}>
                  ₹{payout?.daily_payout}/day
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
                  {(payout?.coverage_ratio * 100).toFixed(0)}% of estimated daily earnings · up to 14 days
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Floor</span>
                  <span>₹{payout?.floor}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginTop: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Ceiling</span>
                  <span>₹{payout?.ceiling}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginTop: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Max 14-day payout</span>
                  <span style={{ fontWeight: 600 }}>₹{(payout?.daily_payout * 14).toLocaleString()}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Zone anomaly protection note */}
          <div className="fade-up-3" style={{
            display: 'flex', gap: 12, alignItems: 'flex-start',
            background: 'var(--surface-2)', borderRadius: 'var(--radius)',
            padding: '14px 16px', border: '1px solid var(--border)'
          }}>
            <Info size={16} color="var(--blue)" style={{ marginTop: 2, flexShrink: 0 }} />
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              <strong style={{ color: 'var(--text-primary)' }}>Zone Anomaly Protection: </strong>
              If your entire zone delivers less this week due to an external cause (bandh, road closure, platform outage),
              the AI detects this automatically. Your contribution is calculated at baseline — you won't be penalised
              for something outside your control.
            </div>
          </div>
        </>
      )}
    </div>
  )
}
import { useState } from 'react'
import { Shield, CheckCircle, ChevronRight, Bike } from 'lucide-react'
import { registerRider, getCities } from '../utils/api'
import { useEffect } from 'react'

const PLATFORMS = ['Swiggy', 'Zomato', 'Dunzo', 'Blinkit', 'Zepto']
const TIER_RATES = { 1: 1.00, 2: 0.75, 3: 0.50 }
const TIER_LABELS = { 1: 'Tier 1 Metro', 2: 'Tier 2 City', 3: 'Tier 3 Town' }

export default function Registration({ onRegister }) {
  const [step, setStep] = useState(1) // 1=form, 2=summary, 3=done
  const [cities, setCities] = useState([])
  const [form, setForm] = useState({
    name: '', phone: '', city: '', platform: '', pincode: '', upi_id: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [registeredRider, setRegisteredRider] = useState(null)

  useEffect(() => {
    getCities().then(r => setCities(r.data)).catch(() => {})
  }, [])

  const selectedCityTier = cities.find(c => c.name === form.city)?.tier || 1
  const estWeeklyContrib = Math.round(90 * TIER_RATES[selectedCityTier])

  const handleChange = (e) => {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }))
    setError('')
  }

  const handleNext = () => {
    if (!form.name || !form.phone || !form.city || !form.platform || !form.pincode) {
      setError('Please fill all required fields.')
      return
    }
    if (!/^\d{10}$/.test(form.phone)) {
      setError('Enter a valid 10-digit phone number.')
      return
    }
    setStep(2)
  }

  const handleRegister = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await registerRider(form)
      setRegisteredRider(res.data)
      setStep(3)
    } catch (e) {
      setError(e.response?.data?.detail || 'Registration failed. Try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleDemoLogin = () => {
    // Use rider ID 1 for demo
    onRegister(1)
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
    }}>
      {/* Background mesh */}
      <div style={{
        position: 'fixed', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse 60% 50% at 50% -10%, rgba(0,212,170,0.08) 0%, transparent 70%)',
      }} />

      <div style={{ width: '100%', maxWidth: 460, position: 'relative' }}>
        {/* Logo */}
        <div className="fade-up" style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16,
            background: 'var(--accent-dim)',
            border: '1px solid rgba(0,212,170,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
          }}>
            <Shield size={26} color="var(--accent)" />
          </div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 28, marginBottom: 6 }}>
            Delivr<span style={{ color: 'var(--accent)' }}>Shield</span>
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
            Income protection for delivery partners
          </p>
        </div>

        {step === 1 && (
          <div className="card fade-up-2" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
              <Bike size={18} color="var(--accent)" />
              <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16 }}>
                Join as a Rider
              </span>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Full Name *</label>
                <input name="name" className="form-input" placeholder="Ravi Kumar"
                  value={form.name} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label className="form-label">Phone *</label>
                <input name="phone" className="form-input" placeholder="9876543210"
                  value={form.phone} onChange={handleChange} maxLength={10} />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">City *</label>
              <select name="city" className="form-input" value={form.city} onChange={handleChange}>
                <option value="">Select your city</option>
                {cities.map(c => (
                  <option key={c.name} value={c.name}>{c.name} (Tier {c.tier})</option>
                ))}
              </select>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Platform *</label>
                <select name="platform" className="form-input" value={form.platform} onChange={handleChange}>
                  <option value="">Select platform</option>
                  {PLATFORMS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Pincode *</label>
                <input name="pincode" className="form-input" placeholder="500001"
                  value={form.pincode} onChange={handleChange} maxLength={6} />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">UPI ID (optional)</label>
              <input name="upi_id" className="form-input" placeholder="yourname@upi"
                value={form.upi_id} onChange={handleChange} />
            </div>

            {form.city && (
              <div style={{
                background: 'var(--accent-dim)', border: '1px solid rgba(0,212,170,0.2)',
                borderRadius: 'var(--radius)', padding: '14px 16px',
              }}>
                <div style={{ fontSize: 12, color: 'var(--accent)', marginBottom: 6, fontWeight: 500 }}>
                  YOUR PLAN — {TIER_LABELS[selectedCityTier]}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                      ₹{TIER_RATES[selectedCityTier]}/delivery · ~₹{estWeeklyContrib}/week
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                      ≈1.5% of weekly earnings · auto-deducted
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--text-primary)' }}>
                      ₹{selectedCityTier === 1 ? '400–900' : selectedCityTier === 2 ? '325–700' : '250–550'}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>payout/day if claimed</div>
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div style={{ color: 'var(--red)', fontSize: 13, background: 'var(--red-dim)', padding: '10px 14px', borderRadius: 'var(--radius)' }}>
                {error}
              </div>
            )}

            <button className="btn btn-primary btn-full" onClick={handleNext}>
              Continue <ChevronRight size={16} />
            </button>

            <div style={{ textAlign: 'center' }}>
              <button
                onClick={handleDemoLogin}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: 13, cursor: 'pointer', textDecoration: 'underline' }}
              >
                Demo: log in as Ravi Kumar (Rider #1)
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="card fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 20 }}>
              Confirm your details
            </h2>

            {[
              ['Name', form.name], ['Phone', form.phone],
              ['City', form.city], ['Platform', form.platform],
              ['Pincode', form.pincode], ['UPI', form.upi_id || '—'],
            ].map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>{k}</span>
                <span style={{ fontWeight: 500 }}>{v}</span>
              </div>
            ))}

            <div style={{
              background: 'var(--accent-dim)', border: '1px solid rgba(0,212,170,0.2)',
              borderRadius: 'var(--radius)', padding: '14px 16px',
              fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6
            }}>
              By registering, you agree that ₹{TIER_RATES[selectedCityTier]}/delivery will be
              auto-deducted from your weekly payout. Coverage activates after 3 full weeks.
            </div>

            {error && (
              <div style={{ color: 'var(--red)', fontSize: 13, background: 'var(--red-dim)', padding: '10px 14px', borderRadius: 'var(--radius)' }}>
                {error}
              </div>
            )}

            <div style={{ display: 'flex', gap: 12 }}>
              <button className="btn btn-secondary" onClick={() => setStep(1)} style={{ flex: 1 }}>
                Back
              </button>
              <button className="btn btn-primary" onClick={handleRegister} disabled={loading} style={{ flex: 2 }}>
                {loading ? <><span className="spinner" style={{ width: 16, height: 16 }} /> Registering…</> : 'Confirm & Register'}
              </button>
            </div>
          </div>
        )}

        {step === 3 && registeredRider && (
          <div className="card fade-up" style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 20, alignItems: 'center' }}>
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              background: 'var(--accent-dim)', border: '2px solid var(--accent)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <CheckCircle size={30} color="var(--accent)" />
            </div>
            <div>
              <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 22, marginBottom: 8 }}>
                Welcome, {registeredRider.name.split(' ')[0]}!
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.6 }}>
                You're registered as Rider #{registeredRider.id}.<br />
                Complete 3 weekly contributions to activate your policy.
              </p>
            </div>
            <div style={{
              width: '100%', background: 'var(--surface-2)', borderRadius: 'var(--radius)',
              padding: '14px 16px', border: '1px solid var(--border)'
            }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Next step</div>
              <div style={{ fontSize: 14, color: 'var(--text-primary)' }}>
                Week 1 of 3 contributions required · Policy activates automatically
              </div>
            </div>
            <button
              className="btn btn-primary btn-full"
              onClick={() => onRegister(registeredRider.id)}
            >
              Go to Dashboard <ChevronRight size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
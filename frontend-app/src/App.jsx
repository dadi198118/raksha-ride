import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState } from 'react'
import Registration from './pages/Registration.jsx'
import Dashboard from './pages/Dashboard.jsx'
import PremiumCalculator from './pages/PremiumCalculator.jsx'
import Claims from './pages/Claims.jsx'
import OpsAdmin from './pages/OpsAdmin.jsx'
import Layout from './components/Layout.jsx'
import './index.css'

export default function App() {
  const [riderId, setRiderId] = useState(() => {
    return localStorage.getItem('raksha_rider_id') || null
  })

  const handleLogin = (id) => {
    localStorage.setItem('raksha_rider_id', String(id))
    setRiderId(String(id))
  }

  const handleLogout = () => {
    localStorage.removeItem('raksha_rider_id')
    setRiderId(null)
  }

  return (
    <Router>
      <Routes>
        <Route path="/register" element={
          riderId
            ? <Navigate to="/dashboard" replace />
            : <Registration onRegister={handleLogin} />
        } />
        <Route path="/" element={
          riderId
            ? <Layout riderId={riderId} onLogout={handleLogout} />
            : <Navigate to="/register" replace />
        }>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard riderId={riderId} />} />
          <Route path="premium" element={<PremiumCalculator riderId={riderId} />} />
          <Route path="claims" element={<Claims riderId={riderId} />} />
          <Route path="ops" element={<OpsAdmin />} />
        </Route>
        <Route path="*" element={<Navigate to="/register" replace />} />
      </Routes>
    </Router>
  )
}
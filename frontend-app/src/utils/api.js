import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 10000,
})

export const getRiders = () => api.get('/riders/')
export const getRider = (id) => api.get(`/riders/${id}`)
export const registerRider = (data) => api.post('/riders/register', data)
export const getRiderDashboard = (id) => api.get(`/riders/${id}/dashboard`)
export const getRiderContributions = (id) => api.get(`/riders/${id}/contributions`)

export const previewPricing = (riderId, deliveries) =>
  api.get(`/pricing/preview/${riderId}?deliveries=${deliveries}`)
export const computePricing = (data) => api.post('/pricing/compute', data)

export const getAlerts = (activeOnly = false) =>
  api.get(`/alerts/?active_only=${activeOnly}`)
export const triggerDetection = () => api.post('/alerts/trigger-detection')
export const mockDisaster = (zoneId, eventType, severity = 4) =>
  api.post(`/alerts/mock-disaster?zone_id=${zoneId}&event_type=${eventType}&severity=${severity}`)

export const getRiderClaims = (riderId) => api.get(`/claims/rider/${riderId}`)
export const checkEligibility = (riderId, alertId) =>
  api.post(`/claims/check-eligibility/${riderId}/${alertId}`)

export const getCities = () => api.get('/cities')
export const getHealth = () => api.get('/health')

export default api

import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: BASE, timeout: 8000 })

export const getStatus    = ()        => api.get('/status')
export const startBot     = ()        => api.post('/start')
export const stopBot      = ()        => api.post('/stop')
export const getPositions = ()        => api.get('/positions')
export const getTrades    = (n = 50)  => api.get(`/trades?limit=${n}`)
export const getAnalysis  = ()        => api.get('/analysis')
export const getCredentials = ()      => api.get('/credentials')
export const saveCredentials = (data) => api.post('/credentials', data)

export default api

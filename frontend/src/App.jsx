import { useState, useEffect, useCallback } from 'react'
import { getCredentials, getStatus } from './api'
import Topbar from './components/Topbar'
import Dashboard from './pages/Dashboard'
import CredentialsPage from './pages/CredentialsPage'
import './App.css'

export default function App() {
  const [tab, setTab] = useState('dashboard')
  const [status, setStatus] = useState({ running: false, total_pnl: 0, win_rate: 0, total_trades: 0, open_positions: 0 })
  const [credsSaved, setCredsSaved] = useState(false)
  const [checkingCreds, setCheckingCreds] = useState(true)

  const refreshStatus = useCallback(async () => {
    try {
      const { data } = await getStatus()
      setStatus(data)
    } catch (_) { /* API not up yet */ }
  }, [])

  // Poll status every 3 seconds
  useEffect(() => {
    refreshStatus()
    const interval = setInterval(refreshStatus, 3000)
    return () => clearInterval(interval)
  }, [refreshStatus])

  // Check if credentials are already saved
  useEffect(() => {
    getCredentials()
      .then(({ data }) => {
        setCredsSaved(!!data.account && !!data.server && data.has_password)
      })
      .catch(() => setCredsSaved(false))
      .finally(() => setCheckingCreds(false))
  }, [])

  if (checkingCreds) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', gap: 12, flexDirection: 'column'
      }}>
        <div style={{ fontSize: '2rem' }}>⚡</div>
        <span className="spinner" style={{ borderTopColor: 'var(--gold)', width: 28, height: 28 }} />
        <span style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>Connecting to XauBot API...</span>
      </div>
    )
  }

  return (
    <div className="app-wrapper">
      <Topbar status={status} tab={tab} setTab={setTab} />

      {tab === 'dashboard' && (
        <Dashboard
          status={status}
          refreshStatus={refreshStatus}
          onGoToSettings={() => setTab('credentials')}
          hasCredentials={credsSaved}
        />
      )}

      {tab === 'credentials' && (
        <CredentialsPage
          onSaved={() => {
            setCredsSaved(true)
            setTab('dashboard')
          }}
        />
      )}
    </div>
  )
}

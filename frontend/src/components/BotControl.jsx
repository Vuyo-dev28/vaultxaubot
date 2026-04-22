import { useState } from 'react'
import { Power, Loader, AlertTriangle } from 'lucide-react'
import { startBot, stopBot } from '../api'

export default function BotControl({ status, onRefresh, onGoToSettings, hasCredentials }) {
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState(null)
  const running = status?.running

  const handleToggle = async () => {
    if (!hasCredentials) {
      setMsg({ type: 'error', text: 'Please save your MT5 credentials first.' })
      return
    }
    setLoading(true)
    setMsg(null)
    try {
      const fn = running ? stopBot : startBot
      const { data } = await fn()
      setMsg({ type: 'success', text: data.message })
      setTimeout(onRefresh, 800)
    } catch (e) {
      setMsg({ type: 'error', text: e?.response?.data?.detail || 'Action failed.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`bot-control-card ${running ? 'running' : ''}`}>
      <div className="bot-info">
        <h2>
          {running ? '🟢 Bot is Running' : '⭕ Bot is Stopped'}
        </h2>
        <p>
          {running
            ? 'Actively monitoring XAUUSD for trade signals on M15'
            : 'Toggle the switch to start the trading bot'}
        </p>
        {msg && (
          <div className={`alert alert-${msg.type === 'error' ? 'error' : 'success'}`} style={{ marginTop: '1rem', marginBottom: 0 }}>
            {msg.text}
          </div>
        )}
        {!hasCredentials && (
          <div className="alert alert-info" style={{ marginTop: '0.75rem', marginBottom: 0 }}>
            <AlertTriangle size={14} />
            <span>
              MT5 credentials not set.{' '}
              <button
                onClick={onGoToSettings}
                style={{ background: 'none', border: 'none', color: 'var(--blue)', textDecoration: 'underline', cursor: 'pointer', font: 'inherit', padding: 0 }}
              >
                Configure now →
              </button>
            </span>
          </div>
        )}
      </div>

      <div className="bot-control-actions">
        <label className="toggle-switch" title={running ? 'Stop Bot' : 'Start Bot'}>
          <input
            type="checkbox"
            checked={running}
            onChange={handleToggle}
            disabled={loading}
          />
          <span className="toggle-track" />
        </label>

        <button
          className={`btn ${running ? 'btn-danger' : 'btn-primary'}`}
          onClick={handleToggle}
          disabled={loading}
          id="bot-toggle-btn"
        >
          {loading ? (
            <><span className="spinner" />  {running ? 'Stopping...' : 'Starting...'}</>
          ) : (
            <><Power size={15} /> {running ? 'Stop Bot' : 'Start Bot'}</>
          )}
        </button>
      </div>
    </div>
  )
}

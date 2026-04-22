import { useState, useEffect } from 'react'
import { Save, Eye, EyeOff, CheckCircle, AlertCircle } from 'lucide-react'
import { saveCredentials, getCredentials } from '../api'

export default function CredentialsPage({ onSaved }) {
  const [form, setForm] = useState({ account: '', password: '', server: '', path: '' })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState(null) // { type: 'success'|'error', text }
  const [fetching, setFetching] = useState(true)

  // Pre-fill existing credentials
  useEffect(() => {
    getCredentials()
      .then(({ data }) => {
        setForm(f => ({
          ...f,
          account: data.account || '',
          server: data.server || '',
          path: data.path || '',
          password: data.has_password ? '••••••••' : '',
        }))
      })
      .catch(() => {})
      .finally(() => setFetching(false))
  }, [])

  const handleChange = (e) => {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }))
    setStatus(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.account || !form.server) {
      setStatus({ type: 'error', text: 'Account number and server are required.' })
      return
    }
    // Don't send masked password placeholder
    const payload = { ...form }
    if (payload.password === '••••••••') delete payload.password

    setLoading(true)
    setStatus(null)
    try {
      await saveCredentials(payload)
      setStatus({ type: 'success', text: 'Credentials saved! You can now start the bot.' })
      setTimeout(() => onSaved?.(), 1200)
    } catch (e) {
      setStatus({ type: 'error', text: e?.response?.data?.detail || 'Failed to save credentials.' })
    } finally {
      setLoading(false)
    }
  }

  if (fetching) {
    return (
      <div className="main-content">
        <div className="setup-card">
          <div className="empty-state">
            <span className="spinner" style={{ borderTopColor: 'var(--gold)' }} />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="main-content">
      <div className="setup-card">
        <div className="setup-title">
          <div className="logo-big">⚡</div>
          <h2>MT5 Account Setup</h2>
          <p>Enter your MetaTrader 5 credentials to connect the bot</p>
        </div>

        {status && (
          <div className={`alert alert-${status.type === 'error' ? 'error' : 'success'}`}>
            {status.type === 'error' ? <AlertCircle size={15} /> : <CheckCircle size={15} />}
            {status.text}
          </div>
        )}

        <form onSubmit={handleSubmit} id="credentials-form">
          <div className="form-group">
            <label className="form-label" htmlFor="input-account">Account Number</label>
            <input
              id="input-account"
              name="account"
              type="text"
              className="form-input"
              placeholder="e.g. 12345678"
              value={form.account}
              onChange={handleChange}
              autoComplete="off"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="input-password">Password</label>
            <div style={{ position: 'relative' }}>
              <input
                id="input-password"
                name="password"
                type={showPass ? 'text' : 'password'}
                className="form-input"
                placeholder="Your MT5 password"
                value={form.password}
                onChange={handleChange}
                autoComplete="current-password"
                style={{ paddingRight: '2.5rem' }}
              />
              <button
                type="button"
                onClick={() => setShowPass(v => !v)}
                style={{
                  position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer',
                  display: 'flex', alignItems: 'center'
                }}
              >
                {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="input-server">Broker Server</label>
            <input
              id="input-server"
              name="server"
              type="text"
              className="form-input"
              placeholder="e.g. Deriv-Server"
              value={form.server}
              onChange={handleChange}
              autoComplete="off"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="input-path">
              MT5 Terminal Path <span style={{ color: 'var(--text-muted)', fontWeight: 400, textTransform: 'none' }}>(optional)</span>
            </label>
            <input
              id="input-path"
              name="path"
              type="text"
              className="form-input"
              placeholder="C:\Program Files\MetaTrader 5\terminal64.exe"
              value={form.path}
              onChange={handleChange}
              autoComplete="off"
            />
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
              Leave blank to use the default MT5 installation path.
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center', marginTop: 8, padding: '12px' }}
            disabled={loading}
            id="save-credentials-btn"
          >
            {loading ? (
              <><span className="spinner" /> Saving...</>
            ) : (
              <><Save size={15} /> Save Credentials</>
            )}
          </button>
        </form>

        <div style={{
          marginTop: '1.5rem',
          padding: '1rem',
          background: 'var(--bg-surface)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border)',
          fontSize: '0.78rem',
          color: 'var(--text-muted)',
          lineHeight: 1.7,
        }}>
          🔒 <strong style={{ color: 'var(--text-secondary)' }}>Security note:</strong> Credentials are stored only in your local <code style={{ color: 'var(--gold)', background: 'rgba(245,200,66,0.08)', padding: '1px 5px', borderRadius: 4 }}>.env</code> file and never sent to any remote server.
        </div>
      </div>
    </div>
  )
}

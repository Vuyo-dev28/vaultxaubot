import { LayoutDashboard, Settings, Bot } from 'lucide-react'

export default function Topbar({ status, tab, setTab }) {
  const running = status?.running

  return (
    <header className="topbar">
      <div className="topbar-logo">
        <div className="logo-icon">⚡</div>
        <span>XauBot</span>
      </div>

      {/* Navigation tabs */}
      <nav style={{ display: 'flex', gap: 4 }}>
        <button
          className={`tab-btn ${tab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setTab('dashboard')}
        >
          <LayoutDashboard size={15} />
          Dashboard
        </button>
        <button
          className={`tab-btn ${tab === 'credentials' ? 'active' : ''}`}
          onClick={() => setTab('credentials')}
        >
          <Settings size={15} />
          MT5 Settings
        </button>
      </nav>

      <div className="topbar-right">
        <div className={`status-pill ${running ? 'running' : 'stopped'}`}>
          <span className="status-dot" />
          {running ? 'Bot Active' : 'Bot Offline'}
        </div>
      </div>
    </header>
  )
}

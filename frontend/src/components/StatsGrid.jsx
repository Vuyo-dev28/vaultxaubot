import { TrendingUp, TrendingDown, Activity, Target } from 'lucide-react'

function StatCard({ label, value, sub, accent, icon: Icon }) {
  return (
    <div className="stat-card" style={{ '--accent-color': accent }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <span className="stat-label">{label}</span>
        {Icon && <Icon size={16} style={{ color: accent, opacity: 0.7 }} />}
      </div>
      <div className={`stat-value ${typeof value === 'string' && value.startsWith('-') ? 'negative' : ''}`}
        style={{ color: accent || 'var(--text-primary)' }}>
        {value}
      </div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

export default function StatsGrid({ status }) {
  const pnl = status?.total_pnl ?? 0
  const pnlFormatted = `${pnl >= 0 ? '+' : ''}$${Math.abs(pnl).toFixed(2)}`
  const wr = status?.win_rate ?? 0
  const trades = status?.total_trades ?? 0
  const open = status?.open_positions ?? 0

  return (
    <div className="stats-grid">
      <StatCard
        label="Total P&L"
        value={pnlFormatted}
        sub="All closed trades"
        accent={pnl >= 0 ? 'var(--green)' : 'var(--red)'}
        icon={pnl >= 0 ? TrendingUp : TrendingDown}
      />
      <StatCard
        label="Win Rate"
        value={`${wr.toFixed(1)}%`}
        sub={`${trades} closed trades`}
        accent="var(--gold)"
        icon={Target}
      />
      <StatCard
        label="Closed Trades"
        value={trades}
        sub="All time"
        accent="var(--blue)"
        icon={Activity}
      />
      <StatCard
        label="Open Positions"
        value={open}
        sub="Currently active"
        accent={open > 0 ? 'var(--green)' : 'var(--text-muted)'}
        icon={Activity}
      />
    </div>
  )
}

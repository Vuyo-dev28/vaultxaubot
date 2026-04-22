import BotControl from '../components/BotControl'
import StatsGrid from '../components/StatsGrid'
import PositionsTable from '../components/PositionsTable'
import TradesTable from '../components/TradesTable'
import AnalysisPanel from '../components/AnalysisPanel'
import { useState } from 'react'
import { LayoutDashboard, History, BarChart2 } from 'lucide-react'

const TABS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'trades',   label: 'Trade History', icon: History },
  { id: 'analysis', label: 'Analysis', icon: BarChart2 },
]

export default function Dashboard({ status, refreshStatus, onGoToSettings, hasCredentials }) {
  const [innerTab, setInnerTab] = useState('overview')
  const now = new Date()
  const greeting = now.getHours() < 12 ? 'Good morning' : now.getHours() < 18 ? 'Good afternoon' : 'Good evening'

  return (
    <main className="main-content">
      {/* Header */}
      <div className="page-header">
        <h1>⚡ XauBot Dashboard</h1>
        <p>{greeting} — {now.toLocaleDateString('en-ZA', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>

      {/* Bot Master Control */}
      <BotControl
        status={status}
        onRefresh={refreshStatus}
        onGoToSettings={onGoToSettings}
        hasCredentials={hasCredentials}
      />

      {/* Stats row */}
      <StatsGrid status={status} />

      {/* Inner tabs */}
      <div className="tabs">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`tab-btn ${innerTab === id ? 'active' : ''}`}
            onClick={() => setInnerTab(id)}
            id={`tab-${id}`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {innerTab === 'overview' && (
        <div>
          <PositionsTable />
        </div>
      )}

      {innerTab === 'trades' && (
        <div>
          <TradesTable />
        </div>
      )}

      {innerTab === 'analysis' && (
        <div>
          <AnalysisPanel />
        </div>
      )}
    </main>
  )
}

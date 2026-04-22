import { useEffect, useState } from 'react'
import { BarChart2, RefreshCw } from 'lucide-react'
import { getAnalysis } from '../api'

export default function AnalysisPanel() {
  const [symbols, setSymbols] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const { data } = await getAnalysis()
      setSymbols(data.symbols || [])
    } catch (_) {}
    finally { setLoading(false) }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [])

  const maxPnl = Math.max(...symbols.map(s => Math.abs(parseFloat(s.PnL || 0))), 1)

  return (
    <div className="card section">
      <div className="card-header">
        <span className="card-title"><BarChart2 size={14} style={{ display: 'inline', marginRight: 6 }} />Performance by Symbol</span>
        <button className="btn btn-ghost" style={{ padding: '5px 10px', fontSize: '0.78rem' }} onClick={load}>
          <RefreshCw size={13} />
        </button>
      </div>

      {loading ? (
        <div className="empty-state">
          <span className="spinner" style={{ borderTopColor: 'var(--gold)' }} />
        </div>
      ) : symbols.length === 0 ? (
        <div className="empty-state">
          <BarChart2 size={32} />
          <span style={{ fontSize: '0.88rem' }}>No analysis data yet</span>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Appears once trades are closed</span>
        </div>
      ) : (
        <div>
          {symbols.map((s, i) => {
            const pnl = parseFloat(s.PnL || 0)
            const wr = parseFloat(s.WinRate || 0)
            const barWidth = (Math.abs(pnl) / maxPnl) * 100
            const isPos = pnl >= 0
            return (
              <div key={i} className="symbol-row">
                <div>
                  <div className="symbol-name">{s.Symbol}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                    {s.Trades} trades
                  </div>
                  {/* Mini bar chart */}
                  <div style={{ marginTop: 8, height: 4, width: 140, background: 'var(--bg-base)', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${barWidth}%`,
                      background: isPos ? 'var(--green)' : 'var(--red)',
                      borderRadius: 4,
                      transition: 'width 0.6s ease',
                    }} />
                  </div>
                </div>
                <div className="symbol-meta">
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>P&L</div>
                    <div className={isPos ? 'pnl-positive' : 'pnl-negative'}>
                      {isPos ? '+' : ''}${pnl.toFixed(2)}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Win Rate</div>
                    <div style={{ color: wr >= 50 ? 'var(--green)' : 'var(--red)', fontWeight: 700 }}>
                      {wr.toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

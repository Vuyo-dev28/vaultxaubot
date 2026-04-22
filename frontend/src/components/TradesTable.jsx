import { useEffect, useState } from 'react'
import { RefreshCw, Clock } from 'lucide-react'
import { getTrades } from '../api'

export default function TradesTable() {
  const [trades, setTrades] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const { data } = await getTrades(50)
      // Most recent first
      setTrades([...(data.trades || [])].reverse())
    } catch (_) {}
    finally { setLoading(false) }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 10000)
    return () => clearInterval(t)
  }, [])

  const pnlColor = (v) => {
    const n = parseFloat(v)
    if (n > 0) return 'var(--green)'
    if (n < 0) return 'var(--red)'
    return 'var(--text-muted)'
  }

  return (
    <div className="card section">
      <div className="card-header">
        <span className="card-title">Recent Closed Trades</span>
        <button className="btn btn-ghost" style={{ padding: '5px 10px', fontSize: '0.78rem' }} onClick={load}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="empty-state">
          <span className="spinner" style={{ borderTopColor: 'var(--gold)' }} />
        </div>
      ) : trades.length === 0 ? (
        <div className="empty-state">
          <Clock size={32} />
          <span style={{ fontSize: '0.88rem' }}>No closed trades yet</span>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Symbol</th>
                <th>Type</th>
                <th>Price</th>
                <th>SL</th>
                <th>TP</th>
                <th>Lots</th>
                <th>P&L</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t, i) => (
                <tr key={i}>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{t.Time}</td>
                  <td style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{t.Symbol}</td>
                  <td>
                    <span className={`badge ${t.Type === 'BUY' ? 'badge-buy' : 'badge-sell'}`}>
                      {t.Type}
                    </span>
                  </td>
                  <td>{parseFloat(t.Price || 0).toFixed(2)}</td>
                  <td style={{ color: 'var(--red)' }}>{parseFloat(t.SL || 0).toFixed(2)}</td>
                  <td style={{ color: 'var(--green)' }}>{parseFloat(t.TP || 0).toFixed(2)}</td>
                  <td>{t.Lots}</td>
                  <td style={{ color: pnlColor(t.Profit), fontWeight: 700 }}>
                    {parseFloat(t.Profit || 0) >= 0 ? '+' : ''}${parseFloat(t.Profit || 0).toFixed(2)}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{t.Comment}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

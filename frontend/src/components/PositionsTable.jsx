import { useEffect, useState } from 'react'
import { RefreshCw, Activity } from 'lucide-react'
import { getPositions } from '../api'

export default function PositionsTable() {
  const [positions, setPositions] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState(null)

  const load = async () => {
    try {
      const { data } = await getPositions()
      setPositions(data.positions || [])
      setLastUpdate(new Date().toLocaleTimeString())
    } catch (_) {}
    finally { setLoading(false) }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="card section">
      <div className="card-header">
        <span className="card-title">Open Positions</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {lastUpdate && <span className="refresh-ts">Updated {lastUpdate}</span>}
          <button className="btn btn-ghost" style={{ padding: '5px 10px', fontSize: '0.78rem' }} onClick={load}>
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="empty-state">
          <span className="spinner" style={{ borderTopColor: 'var(--gold)' }} />
        </div>
      ) : positions.length === 0 ? (
        <div className="empty-state">
          <Activity size={32} />
          <span style={{ fontSize: '0.88rem' }}>No open positions</span>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Type</th>
                <th>Price</th>
                <th>SL</th>
                <th>TP</th>
                <th>Lots</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p, i) => (
                <tr key={i}>
                  <td style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{p.Symbol}</td>
                  <td>
                    <span className={`badge ${p.Type === 'BUY' ? 'badge-buy' : 'badge-sell'}`}>
                      {p.Type}
                    </span>
                  </td>
                  <td>{parseFloat(p.Price || 0).toFixed(2)}</td>
                  <td style={{ color: 'var(--red)' }}>{parseFloat(p.SL || 0).toFixed(2)}</td>
                  <td style={{ color: 'var(--green)' }}>{parseFloat(p.TP || 0).toFixed(2)}</td>
                  <td>{p.Lots}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{p.Time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

'use client'

import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, type RumSummary, type Synthetic } from '@/lib/api'

export default function RumPage() {
  const [rum, setRum] = useState<RumSummary | null>(null)
  const [syn, setSyn] = useState<Synthetic[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.rum(), api.synthetics()])
      .then(([r, s]) => {
        setRum(r)
        setSyn(s)
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  const maxSessions = Math.max(...(rum?.top_views || []).map((v) => v.sessions), 1)

  return (
    <div>
      <h1 className="page-title">RUM & Synthetics</h1>
      <p className="page-sub">Experiência real de usuário + probes sintéticos (estilo Datadog).</p>
      {error && <p className="error">{error}</p>}

      <div className="grid grid-4" style={{ marginBottom: '1rem' }}>
        <div className="card">
          <h3>Sessions 30d</h3>
          <div className="value">{rum?.sessions_30d.toLocaleString('pt-BR') ?? '—'}</div>
        </div>
        <div className="card">
          <h3>Avg LCP</h3>
          <div className="value">{rum ? `${rum.avg_lcp_ms} ms` : '—'}</div>
        </div>
        <div className="card">
          <h3>JS errors</h3>
          <div className="value">{rum?.js_errors ?? '—'}</div>
        </div>
        <div className="card">
          <h3>Crash-free</h3>
          <div className="value">{rum ? `${rum.crash_free_pct}%` : '—'}</div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3 style={{ color: 'var(--text)' }}>Top views</h3>
          <div className="toplist" style={{ marginTop: 8 }}>
            {(rum?.top_views || []).map((v) => (
              <div key={v.view} className="toplist-row">
                <div className="toplist-meta">
                  <span>{v.view}</span>
                  <strong>
                    {v.sessions.toLocaleString('pt-BR')} · {v.errors} err
                  </strong>
                </div>
                <div className="toplist-bar">
                  <div style={{ width: `${(v.sessions / maxSessions) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <h3 style={{ color: 'var(--text)' }}>Synthetics</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Locations</th>
                <th>Uptime</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {syn.map((s) => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td>{s.type}</td>
                  <td>{s.locations}</td>
                  <td>{s.uptime_pct}%</td>
                  <td>
                    <span className={`badge ${s.status === 'OK' ? 'ok' : 'high'}`}>{s.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rum && (
            <div className="chart-box" style={{ height: 160, marginTop: 12 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={(rum.top_views || []).map((v) => ({
                    name: v.view,
                    sessions: v.sessions,
                    errors: v.errors,
                  }))}
                >
                  <CartesianGrid stroke="#243044" strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fill: '#8b9cb3', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#8b9cb3', fontSize: 11 }} width={40} />
                  <Tooltip contentStyle={{ background: '#151b26', border: '1px solid #243044' }} />
                  <Area type="monotone" dataKey="errors" stroke="#fa896b" fill="#fa896b33" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

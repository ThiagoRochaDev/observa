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
import { api, type GcpMonitoring, type LogRow } from '@/lib/api'

type Tab = 'monitoring' | 'logging'

export default function GcpPage() {
  const [tab, setTab] = useState<Tab>('monitoring')
  const [data, setData] = useState<GcpMonitoring | null>(null)
  const [logs, setLogs] = useState<LogRow[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      api.gcpMonitoring(),
      api.logs({ limit: 40, source: 'cloud-logging', severity: 'ERROR' }),
    ])
      .then(([m, l]) => {
        setData(m)
        setLogs(l)
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  return (
    <div>
      <h1 className="page-title">GCP Cloud Monitoring</h1>
      <p className="page-sub">
        Métricas nativas GCP + amostra de Cloud Logging errors — o que Monitoring/Logging expõem,
        agregado no Observa (demo).
      </p>
      {error && <p className="error">{error}</p>}

      <div className="row" style={{ marginBottom: '1rem' }}>
        <button
          type="button"
          className={`btn ${tab === 'monitoring' ? 'btn-primary' : ''}`}
          onClick={() => setTab('monitoring')}
        >
          Cloud Monitoring
        </button>
        <button
          type="button"
          className={`btn ${tab === 'logging' ? 'btn-primary' : ''}`}
          onClick={() => setTab('logging')}
        >
          Cloud Logging
        </button>
      </div>

      {tab === 'monitoring' && (
        <>
          {data && <p className="muted">Project: {data.project}</p>}
          <div className="grid grid-2" style={{ marginTop: '1rem' }}>
            {(data?.metrics || []).map((m) => (
              <div className="card" key={m.type}>
                <h3>{m.display}</h3>
                <div className="muted" style={{ fontSize: '0.72rem', marginBottom: 8 }}>
                  {m.type}
                </div>
                <div className="chart-box">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={m.series}>
                      <CartesianGrid stroke="#243044" strokeDasharray="3 3" />
                      <XAxis dataKey="ts" hide />
                      <YAxis tick={{ fill: '#8b9cb3', fontSize: 11 }} width={42} />
                      <Tooltip
                        contentStyle={{ background: '#151b26', border: '1px solid #243044' }}
                      />
                      <Area type="monotone" dataKey="value" stroke="#4285F4" fill="#4285F433" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {tab === 'logging' && (
        <div className="card log-explorer">
          <h3 style={{ color: 'var(--text)', marginBottom: 12 }}>
            ERROR logs · source=cloud-logging
          </h3>
          <table className="table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Service</th>
                <th>Message</th>
                <th>Trace</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l, i) => (
                <tr key={`${l.ts}-${i}`}>
                  <td className="muted">{l.ts.slice(11, 19)}</td>
                  <td>
                    {l.product}/{l.service}
                  </td>
                  <td className="log-error">{l.message}</td>
                  <td className="muted">{l.trace_id}</td>
                </tr>
              ))}
              {!logs.length && (
                <tr>
                  <td colSpan={4} className="muted">
                    Sem erros Cloud Logging no momento.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

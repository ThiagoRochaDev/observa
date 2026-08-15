'use client'

import { useEffect, useState } from 'react'
import { api, type TraceRow } from '@/lib/api'

export default function TracesPage() {
  const [traces, setTraces] = useState<TraceRow[]>([])
  const [selected, setSelected] = useState<TraceRow | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .traces()
      .then((rows) => {
        setTraces(rows)
        setSelected(rows[0] || null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  const total = selected?.duration_ms || 1

  return (
    <div>
      <h1 className="page-title">APM Traces</h1>
      <p className="page-sub">
        Lista de traces (estilo Datadog APM) com waterfall de spans — demo mock.
      </p>
      {error && <p className="error">{error}</p>}

      <div className="grid grid-2">
        <div className="card">
          <h3 style={{ color: 'var(--text)' }}>Recent traces</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Trace</th>
                <th>Service</th>
                <th>Resource</th>
                <th>Duration</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {traces.map((t) => (
                <tr
                  key={t.trace_id}
                  className={selected?.trace_id === t.trace_id ? 'row-selected' : ''}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelected(t)}
                >
                  <td className="muted">{t.trace_id}</td>
                  <td>
                    {t.product}/{t.service}
                  </td>
                  <td>{t.resource}</td>
                  <td>{t.duration_ms} ms</td>
                  <td>
                    <span className={`badge ${t.status === 'error' ? 'high' : 'ok'}`}>{t.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3 style={{ color: 'var(--text)' }}>
            Span waterfall {selected ? `· ${selected.trace_id}` : ''}
          </h3>
          {!selected && <p className="muted">Selecione um trace.</p>}
          {selected && (
            <>
              <p className="muted" style={{ marginBottom: 12 }}>
                {selected.resource} · {selected.spans} spans · {selected.duration_ms} ms
              </p>
              <div className="span-waterfall">
                {(selected.span_details || []).map((s, i) => (
                  <div key={`${s.name}-${i}`} className="span-row">
                    <div className="span-label">
                      <strong>{s.service}</strong>
                      <span className="muted">{s.name}</span>
                    </div>
                    <div className="span-track">
                      <div
                        className={`span-bar ${s.status === 'error' ? 'error' : ''}`}
                        style={{
                          marginLeft: `${(s.start_ms / total) * 100}%`,
                          width: `${Math.max((s.duration_ms / total) * 100, 2)}%`,
                        }}
                        title={`${s.duration_ms} ms`}
                      />
                    </div>
                    <div className="span-dur muted">{s.duration_ms} ms</div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

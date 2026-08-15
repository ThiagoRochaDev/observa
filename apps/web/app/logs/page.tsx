'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api, type LogRow } from '@/lib/api'

export default function LogsPage() {
  const [logs, setLogs] = useState<LogRow[]>([])
  const [product, setProduct] = useState('')
  const [severity, setSeverity] = useState('')
  const [source, setSource] = useState('')
  const [query, setQuery] = useState('')
  const [draft, setDraft] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .logs({
        limit: 100,
        product: product || undefined,
        severity: severity || undefined,
        source: source || undefined,
        q: query || undefined,
      })
      .then(setLogs)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [product, severity, source, query])

  return (
    <div>
      <h1 className="page-title">Logs</h1>
      <p className="page-sub">
        Explorer unificado — Cloud Logging (GCP) + agent-style logs (Datadog). Filtre por produto,
        severidade, source e query.
      </p>
      <div className="row" style={{ marginBottom: '1rem' }}>
        <input
          style={{ minWidth: 220, flex: 1 }}
          placeholder='query: "timeout", panic, checkout…'
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') setQuery(draft.trim())
          }}
        />
        <button type="button" className="btn btn-primary" onClick={() => setQuery(draft.trim())}>
          Run query
        </button>
        <select value={product} onChange={(e) => setProduct(e.target.value)}>
          <option value="">todos produtos</option>
          {['painel', 'hiperlocal', 'gertrudes', 'delivery', 'platform'].map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">todas severidades</option>
          {['INFO', 'WARN', 'ERROR', 'DEBUG'].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select value={source} onChange={(e) => setSource(e.target.value)}>
          <option value="">todas sources</option>
          <option value="cloud-logging">cloud-logging</option>
          <option value="datadog-agent">datadog-agent</option>
        </select>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="muted" style={{ marginBottom: 8 }}>
        {logs.length} eventos
        {query ? ` · q="${query}"` : ''}
      </div>
      <div className="card log-explorer">
        <table className="table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Sev</th>
              <th>Service</th>
              <th>Source</th>
              <th>Message</th>
              <th>Trace</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l, i) => (
              <tr key={`${l.ts}-${i}`}>
                <td className="muted">{l.ts.slice(11, 19)}</td>
                <td>
                  <span
                    className={
                      l.severity === 'ERROR' ? 'log-error' : l.severity === 'WARN' ? 'log-warn' : 'log-info'
                    }
                  >
                    {l.severity}
                  </span>
                </td>
                <td>
                  {l.product}/{l.service}
                </td>
                <td>
                  <span className="badge">{l.source}</span>
                </td>
                <td className="log-msg">{l.message}</td>
                <td>
                  {l.trace_id ? (
                    <Link className="muted" href="/traces">
                      {l.trace_id}
                    </Link>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
            {!logs.length && !error && (
              <tr>
                <td colSpan={6} className="muted">
                  Nenhum log para os filtros atuais.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

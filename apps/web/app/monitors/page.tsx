'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { api, type Monitor } from '@/lib/api'

export default function MonitorsPage() {
  const [items, setItems] = useState<Monitor[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .monitors()
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  const counts = useMemo(() => {
    const c = { Alert: 0, Warn: 0, OK: 0 }
    for (const m of items) {
      if (m.status in c) c[m.status as keyof typeof c] += 1
      else c.OK += 1
    }
    return c
  }, [items])

  return (
    <div>
      <h1 className="page-title">Monitors</h1>
      <p className="page-sub">
        Alertas de métrica, log e FinOps — equivalente a Datadog Monitors + GCP Alerting policies.
      </p>
      {error && <p className="error">{error}</p>}

      <div className="grid grid-4" style={{ marginBottom: '1rem' }}>
        <div className="card">
          <h3>Total</h3>
          <div className="value">{items.length}</div>
        </div>
        <div className="card">
          <h3>Alert</h3>
          <div className="value" style={{ color: 'var(--danger)' }}>
            {counts.Alert}
          </div>
        </div>
        <div className="card">
          <h3>Warn</h3>
          <div className="value" style={{ color: 'var(--warning)' }}>
            {counts.Warn}
          </div>
        </div>
        <div className="card">
          <h3>OK</h3>
          <div className="value" style={{ color: 'var(--success)' }}>
            {counts.OK}
          </div>
        </div>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Name</th>
              <th>Type</th>
              <th>Product</th>
              <th>Query</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {items.map((m) => (
              <tr key={m.id}>
                <td>
                  <span
                    className={`badge ${
                      m.status === 'Alert' ? 'high' : m.status === 'Warn' ? 'medium' : 'ok'
                    }`}
                  >
                    {m.status}
                  </span>
                </td>
                <td>
                  <strong>{m.name}</strong>
                </td>
                <td>{m.type}</td>
                <td>
                  {m.product ? <Link href={`/products/${m.product}`}>{m.product}</Link> : '—'}
                </td>
                <td className="muted" style={{ maxWidth: 280, wordBreak: 'break-word' }}>
                  {m.query}
                </td>
                <td>
                  <span className="badge">{m.source}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

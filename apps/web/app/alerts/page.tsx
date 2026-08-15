'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api, type Alert } from '@/lib/api'

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .alerts()
      .then(setAlerts)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  return (
    <div>
      <h1 className="page-title">Alertas</h1>
      <p className="page-sub">
        Custo, APM, banco e recomendações FinOps — centralizados por produto.
      </p>
      {error && <p className="error">{error}</p>}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Severidade</th>
              <th>Categoria</th>
              <th>Produto</th>
              <th>Alerta</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.id}>
                <td>
                  <span className={`badge ${a.severity}`}>{a.severity}</span>
                </td>
                <td>
                  <span className="badge">{a.category}</span>
                </td>
                <td>
                  {a.product ? <Link href={`/products/${a.product}`}>{a.product}</Link> : '—'}
                </td>
                <td>
                  <strong>{a.title}</strong>
                  <div className="muted">{a.message}</div>
                </td>
                <td>
                  <span className={`badge ${a.status === 'open' ? 'high' : 'ok'}`}>{a.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

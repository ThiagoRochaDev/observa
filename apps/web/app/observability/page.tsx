'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api, type ObservabilityOverview } from '@/lib/api'

export default function ObservabilityPage() {
  const [data, setData] = useState<ObservabilityOverview | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .observability()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  return (
    <div>
      <h1 className="page-title">Observabilidade</h1>
      <p className="page-sub">
        APM + infra + banco por produto — no estilo Datadog / GCP Monitoring / Percona, agregados no
        catálogo Observa.
      </p>
      {error && <p className="error">{error}</p>}

      <div className="grid grid-3" style={{ marginBottom: '1rem' }}>
        <div className="card">
          <h3>Séries ativas</h3>
          <div className="value">{data?.metric_count ?? '—'}</div>
        </div>
        <div className="card">
          <h3>Produtos monitorados</h3>
          <div className="value">{data?.products.length ?? '—'}</div>
        </div>
        <div className="card">
          <h3>Alertas</h3>
          <div className="value">{data?.alert_count ?? '—'}</div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ color: 'var(--text)', marginBottom: '0.75rem' }}>Health por produto</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Produto</th>
              <th>P95 ms</th>
              <th>Error %</th>
              <th>RPM</th>
              <th>CPU %</th>
              <th>DB conn</th>
              <th>DB CPU %</th>
            </tr>
          </thead>
          <tbody>
            {(data?.products || []).map((p) => (
              <tr key={p.product}>
                <td>
                  <Link href={`/products/${p.product}`}>
                    <strong>{p.product}</strong>
                  </Link>
                </td>
                <td>{p.latency_p95_ms ?? '—'}</td>
                <td>
                  <span className={`badge ${(p.error_rate_pct || 0) > 1.5 ? 'high' : 'ok'}`}>
                    {p.error_rate_pct ?? '—'}
                  </span>
                </td>
                <td>{p.rpm ?? '—'}</td>
                <td>{p.cpu_pct ?? '—'}</td>
                <td>{p.db_connections ?? '—'}</td>
                <td>{p.db_cpu_pct ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

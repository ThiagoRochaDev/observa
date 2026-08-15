'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api, type DashboardMeta } from '@/lib/api'

export default function DashboardsPage() {
  const [items, setItems] = useState<DashboardMeta[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .dashboards()
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  return (
    <div>
      <h1 className="page-title">Dashboards</h1>
      <p className="page-sub">
        Painéis no estilo Datadog / Cloud Monitoring — APM, infra, banco, logs e RUM (demo).
      </p>
      {error && <p className="error">{error}</p>}
      <div className="grid grid-2">
        {items.map((d) => (
          <Link key={d.id} href={`/dashboards/${d.id}`} className="card">
            <h3 style={{ color: 'var(--text)' }}>{d.title}</h3>
            <p className="muted" style={{ margin: '0.4rem 0 0.7rem' }}>
              {d.description}
            </p>
            <div className="row">
              <span className="badge">{d.source}</span>
              <span className="badge">{d.widgets} widgets</span>
              {d.tags.map((t) => (
                <span key={t} className="badge">
                  {t}
                </span>
              ))}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

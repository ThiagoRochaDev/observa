'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api, type Resource } from '@/lib/api'

export default function InventoryPage() {
  const [resources, setResources] = useState<Resource[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .resources()
      .then(setResources)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  return (
    <div>
      <h1 className="page-title">Inventário cloud</h1>
      <p className="page-sub">
        GKE, Cloud Run, Cloud SQL, ElastiCache e afins — discovery via conectores.
      </p>
      {error && <p className="error">{error}</p>}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Produto</th>
              <th>Tipo</th>
              <th>Nome</th>
              <th>Provider</th>
              <th>Região</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {resources.map((r) => (
              <tr key={`${r.provider}-${r.id}`}>
                <td>
                  {r.product ? <Link href={`/products/${r.product}`}>{r.product}</Link> : '—'}
                </td>
                <td>
                  <span className="badge">{r.type}</span>
                </td>
                <td>{r.name || r.id}</td>
                <td>{r.provider}</td>
                <td>{r.region || '—'}</td>
                <td>
                  <span className="badge ok">{r.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

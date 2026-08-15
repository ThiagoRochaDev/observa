'use client'

import dynamic from 'next/dynamic'
import { useEffect, useState } from 'react'
import { api, type Ecosystem } from '@/lib/api'

const EcosystemMap = dynamic(
  () => import('@/components/EcosystemMap').then((m) => m.EcosystemMap),
  { ssr: false, loading: () => <p className="muted">Carregando mapa…</p> },
)

const PRODUCTS = ['hiperlocal', 'painel', 'gertrudes', 'delivery', 'platform']

export default function MapsPage() {
  const [product, setProduct] = useState('hiperlocal')
  const [eco, setEco] = useState<Ecosystem | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .ecosystem(product)
      .then(setEco)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [product])

  return (
    <div>
      <h1 className="page-title">Mapas de ecossistema</h1>
      <p className="page-sub">
        Serviços, workers, bancos e integrações externas por produto, num mapa de ecossistema
        navegável.
      </p>
      <div className="row" style={{ marginBottom: '1rem' }}>
        {PRODUCTS.map((p) => (
          <button
            key={p}
            type="button"
            className={`btn ${product === p ? 'btn-primary' : ''}`}
            onClick={() => setProduct(p)}
          >
            {p}
          </button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
      <div className="row" style={{ marginBottom: '0.75rem' }}>
        {[
          ['frontend', '#3b82f6'],
          ['api', '#22c55e'],
          ['worker', '#f59e0b'],
          ['resource', '#64748b'],
          ['external', '#a855f7'],
        ].map(([k, c]) => (
          <span key={k} className="badge">
            <span className="legend-dot" style={{ background: c }} />
            {k}
          </span>
        ))}
      </div>
      {eco && <EcosystemMap data={eco} />}
    </div>
  )
}

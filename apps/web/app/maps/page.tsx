'use client'

import dynamic from 'next/dynamic'
import { useEffect, useState } from 'react'
import { api, type Ecosystem } from '@/lib/api'

const EcosystemMap = dynamic(
  () => import('@/components/EcosystemMap').then((module) => module.EcosystemMap),
  { ssr: false, loading: () => <div className="live-map-loading">Carregando topologia…</div> },
)

const PRODUCTS = ['hiperlocal', 'painel', 'gertrudes', 'delivery', 'platform']

export default function MapsPage() {
  const [product, setProduct] = useState('hiperlocal')
  const [ecosystem, setEcosystem] = useState<Ecosystem | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    api
      .ecosystem(product)
      .then((result) => {
        if (active) setEcosystem(result)
      })
      .catch((caughtError) => {
        if (active) setError(caughtError instanceof Error ? caughtError.message : String(caughtError))
      })

    return () => {
      active = false
    }
  }, [product])

  function changeProduct(nextProduct: string) {
    setError(null)
    setEcosystem(null)
    setProduct(nextProduct)
  }

  return (
    <div className="live-map-page">
      <header className="live-map-page-head">
        <div>
          <span className="live-map-eyebrow">Mapa vivo da operação</span>
          <h1 className="page-title">Ecossistema de produtos</h1>
          <p className="page-sub">Custos, dependências e contexto técnico em uma única visão navegável.</p>
        </div>
        <label className="live-map-product-select">
          <span>Produto observado</span>
          <select value={product} onChange={(event) => changeProduct(event.target.value)}>
            {PRODUCTS.map((productName) => (
              <option key={productName} value={productName}>{productName}</option>
            ))}
          </select>
        </label>
      </header>

      <div className="live-map-legend" aria-label="Legenda de componentes">
        {Object.entries({ frontend: 'Frontend', api: 'API', worker: 'Worker', resource: 'Cloud resource', external: 'External' }).map(([kind, label]) => (
          <span key={kind}><i className={`legend-${kind}`} />{label}</span>
        ))}
      </div>

      {error && <div className="live-map-error" role="alert">Não foi possível carregar o mapa: {error}</div>}
      {!error && !ecosystem && <div className="live-map-loading">Sincronizando o ecossistema de {product}…</div>}
      {ecosystem && <EcosystemMap key={ecosystem.product} data={ecosystem} />}
    </div>
  )
}

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api, formatMoney, type Product } from '@/lib/api'

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .products()
      .then(setProducts)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  return (
    <div>
      <h1 className="page-title">Catálogo de produtos</h1>
      <p className="page-sub">
        Produtos de negócio com custo, serviços e recursos cloud, agrupados por squad/tribe.
      </p>
      {error && <p className="error">{error}</p>}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Produto</th>
              <th>Squad</th>
              <th>Tribo</th>
              <th>Custo 30d</th>
              <th>Serviços</th>
              <th>Recursos</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.slug}>
                <td>
                  <Link href={`/products/${p.slug}`}>
                    <strong>{p.name || p.slug}</strong>
                  </Link>
                  <div className="muted">{p.slug}</div>
                  {!!p.aliases?.length && (
                    <div className="pill-row">
                      {p.aliases.map((a) => (
                        <span key={a} className="badge">
                          {a}
                        </span>
                      ))}
                    </div>
                  )}
                </td>
                <td>{p.squad}</td>
                <td>{p.tribe}</td>
                <td>{formatMoney(p.total_brl)}</td>
                <td>{p.service_count}</td>
                <td>{p.resource_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

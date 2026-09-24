'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import {
  api,
  CATEGORY_LABELS,
  type Connection,
  type Connector,
  type JsonSchema,
} from '@/lib/api'
import ConnectorIcon from '@/components/ConnectorIcon'

function fieldsFromSchema(schema: JsonSchema) {
  return Object.entries(schema.properties || {}).map(([key, def]) => ({
    key,
    title: def.title || key,
    type: def.type || 'string',
    defaultValue: def.default,
  }))
}

const CATEGORY_ORDER = ['demo', 'cloud', 'observability', 'incident', 'vcs_cicd', 'on_prem', 'saas']

export default function ConnectionsPage() {
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [connections, setConnections] = useState<Connection[]>([])
  const [connectorId, setConnectorId] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [config, setConfig] = useState<Record<string, string>>({})
  const [secrets, setSecrets] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const selected = useMemo(
    () => connectors.find((c) => c.id === connectorId) || null,
    [connectors, connectorId],
  )

  const grouped = useMemo(() => {
    const byCategory = new Map<string, Connector[]>()
    for (const c of connectors) {
      const list = byCategory.get(c.category) || []
      list.push(c)
      byCategory.set(c.category, list)
    }
    return CATEGORY_ORDER.filter((cat) => byCategory.has(cat)).map((cat) => ({
      category: cat,
      items: byCategory.get(cat)!,
    }))
  }, [connectors])

  const refresh = () =>
    Promise.all([api.connectors(), api.connections()]).then(([c, n]) => {
      setConnectors(c)
      setConnections(n)
    })

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  function selectConnector(c: Connector) {
    setConnectorId(c.id)
    setName(c.name)
    const next: Record<string, string> = {}
    for (const f of fieldsFromSchema(c.config_schema)) {
      next[f.key] = f.defaultValue != null ? String(f.defaultValue) : ''
    }
    setConfig(next)
    setSecrets({})
    setMsg(null)
    setError(null)
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    if (!selected) return
    setBusy(true)
    setError(null)
    setMsg(null)
    try {
      const parsedConfig: Record<string, unknown> = {}
      for (const f of fieldsFromSchema(selected.config_schema)) {
        const raw = config[f.key]
        parsedConfig[f.key] = f.type === 'integer' ? Number(raw) : raw
      }
      await api.createConnection({
        name,
        connector_id: selected.id,
        config: parsedConfig,
        secrets,
      })
      setMsg('Connection saved.')
      setConnectorId(null)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onTest() {
    if (!selected) return
    setBusy(true)
    setError(null)
    try {
      const parsedConfig: Record<string, unknown> = {}
      for (const f of fieldsFromSchema(selected.config_schema)) {
        const raw = config[f.key]
        parsedConfig[f.key] = f.type === 'integer' ? Number(raw) : raw
      }
      const res = await api.testConnection({
        connector_id: selected.id,
        config: parsedConfig,
        secrets,
      })
      setMsg(res.message || (res.ok ? 'OK' : 'Failed'))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onSync(id: string) {
    setBusy(true)
    setError(null)
    try {
      const res = await api.syncConnection(id)
      setMsg(`${res.status}: ${res.message}`)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onDelete(id: string) {
    setBusy(true)
    try {
      await api.deleteConnection(id)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h1 className="page-title">Conexões</h1>
      <p className="page-sub">
        Conecte clouds, observabilidade, incidentes, repositórios e ambientes privados. Credenciais
        são criptografadas no servidor e nunca voltam a ser exibidas.
      </p>

      {error && <p className="error">{error}</p>}
      {msg && <p className="muted">{msg}</p>}

      {!selected && (
        <div className="connector-catalog">
          {grouped.map(({ category, items }) => (
            <section key={category} className="connector-category">
              <h2>
                {CATEGORY_LABELS[category] || category}
              </h2>
              <div className="connector-grid">
                {items.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    className="card connector-catalog-card"
                    onClick={() => selectConnector(c)}
                  >
                    <ConnectorIcon icon={c.icon} size={44} />
                    <div className="connector-card-copy">
                      <strong>{c.name}</strong>
                      <div className="muted">
                        {c.description}
                      </div>
                      <div className="row" style={{ marginTop: 6, flexWrap: 'wrap', gap: 4 }}>
                        {c.capabilities.map((cap) => (
                          <span key={cap} className="badge">
                            {cap}
                          </span>
                        ))}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      {selected && (
        <div className="card" style={{ marginBottom: '1.25rem' }}>
          <div className="row connector-form-head">
            <ConnectorIcon icon={selected.icon} size={48} />
            <div>
              <h3 style={{ color: 'var(--text)' }}>{selected.name}</h3>
              <p className="muted" style={{ fontSize: '0.85rem' }}>{selected.description}</p>
            </div>
            <button
              type="button"
              className="btn"
              style={{ marginLeft: 'auto' }}
              onClick={() => setConnectorId(null)}
            >
              ← Back to catalog
            </button>
          </div>
          {selected.docs_url && (
            <p className="muted" style={{ fontSize: '0.8rem', marginBottom: '0.75rem' }}>
              Where to get credentials:{' '}
              <a href={selected.docs_url} target="_blank" rel="noreferrer">
                {selected.docs_url}
              </a>
            </p>
          )}
          <form className="form" onSubmit={onCreate}>
            <label>
              Display name
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </label>
            {fieldsFromSchema(selected.config_schema).map((f) => (
              <label key={f.key}>
                {f.title}
                <input
                  value={config[f.key] ?? ''}
                  onChange={(e) => setConfig({ ...config, [f.key]: e.target.value })}
                />
              </label>
            ))}
            {fieldsFromSchema(selected.secrets_schema).map((f) => (
              <label key={f.key}>
                {f.title}
                <textarea
                  value={secrets[f.key] ?? ''}
                  onChange={(e) => setSecrets({ ...secrets, [f.key]: e.target.value })}
                  placeholder="Stored encrypted on the server — never shown again"
                />
              </label>
            ))}
            <div className="row">
              <button className="btn" type="button" onClick={onTest} disabled={busy}>
                Test connection
              </button>
              <button className="btn btn-primary" type="submit" disabled={busy}>
                Save connection
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <h3 style={{ marginBottom: '0.75rem', color: 'var(--text)' }}>Conexões salvas</h3>
        {connections.length === 0 ? (
          <p className="muted">No connections yet — pick a tool above to add one.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Connector</th>
                <th>Last sync</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {connections.map((c) => {
                const connector = connectors.find((item) => item.id === c.connector_id)
                return (
                <tr key={c.id}>
                  <td>
                    <div className="saved-connection-name">
                      <ConnectorIcon icon={connector?.icon || 'generic'} size={30} />
                      <span>{c.name}</span>
                    </div>
                  </td>
                  <td><span className="badge">{connector?.name || c.connector_id}</span></td>
                  <td>
                    {c.last_sync_status ? (
                      <span className={`badge ${c.last_sync_status === 'ok' ? 'ok' : 'fail'}`}>
                        {c.last_sync_status}
                      </span>
                    ) : (
                      <span className="muted">never</span>
                    )}
                    {c.last_sync_message && (
                      <div className="muted" style={{ marginTop: 4 }}>
                        {c.last_sync_message}
                      </div>
                    )}
                  </td>
                  <td>
                    <div className="row">
                      <button className="btn btn-primary" type="button" disabled={busy} onClick={() => onSync(c.id)}>
                        Sync
                      </button>
                      <button className="btn btn-danger" type="button" disabled={busy} onClick={() => onDelete(c.id)}>
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

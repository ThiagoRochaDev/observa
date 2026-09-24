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
  const [view, setView] = useState<'catalog' | 'installed'>('catalog')
  const [category, setCategory] = useState('all')
  const [query, setQuery] = useState('')
  const [name, setName] = useState('')
  const [config, setConfig] = useState<Record<string, string>>({})
  const [secrets, setSecrets] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const selected = useMemo(
    () => connectors.find((connector) => connector.id === connectorId) || null,
    [connectors, connectorId],
  )

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const connector of connectors) counts[connector.category] = (counts[connector.category] || 0) + 1
    return counts
  }, [connectors])

  const filteredConnectors = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    return connectors.filter((connector) => {
      if (category !== 'all' && connector.category !== category) return false
      if (!normalizedQuery) return true
      return [connector.name, connector.description, connector.category, ...connector.capabilities]
        .join(' ')
        .toLowerCase()
        .includes(normalizedQuery)
    })
  }, [category, connectors, query])

  const grouped = useMemo(() => {
    const byCategory = new Map<string, Connector[]>()
    for (const connector of filteredConnectors) {
      const list = byCategory.get(connector.category) || []
      list.push(connector)
      byCategory.set(connector.category, list)
    }
    return CATEGORY_ORDER.filter((item) => byCategory.has(item)).map((item) => ({
      category: item,
      items: byCategory.get(item)!,
    }))
  }, [filteredConnectors])

  const filteredConnections = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    if (!normalizedQuery) return connections
    return connections.filter((connection) => {
      const connector = connectors.find((item) => item.id === connection.connector_id)
      return `${connection.name} ${connection.connector_id} ${connector?.name || ''}`
        .toLowerCase()
        .includes(normalizedQuery)
    })
  }, [connections, connectors, query])

  const refresh = () =>
    Promise.all([api.connectors(), api.connections()]).then(([connectorRows, connectionRows]) => {
      setConnectors(connectorRows)
      setConnections(connectionRows)
    })

  useEffect(() => {
    refresh().catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)))
  }, [])

  function selectConnector(connector: Connector) {
    setConnectorId(connector.id)
    setName(connector.name)
    const nextConfig: Record<string, string> = {}
    for (const field of fieldsFromSchema(connector.config_schema)) {
      nextConfig[field.key] = field.defaultValue != null ? String(field.defaultValue) : ''
    }
    setConfig(nextConfig)
    setSecrets({})
    setMsg(null)
    setError(null)
  }

  function selectView(nextView: 'catalog' | 'installed') {
    setView(nextView)
    setConnectorId(null)
    setCategory('all')
    setQuery('')
  }

  async function onCreate(event: FormEvent) {
    event.preventDefault()
    if (!selected) return
    setBusy(true)
    setError(null)
    setMsg(null)
    try {
      const parsedConfig: Record<string, unknown> = {}
      for (const field of fieldsFromSchema(selected.config_schema)) {
        const raw = config[field.key]
        parsedConfig[field.key] = field.type === 'integer' ? Number(raw) : raw
      }
      await api.createConnection({ name, connector_id: selected.id, config: parsedConfig, secrets })
      setMsg(`${name} foi conectado com segurança.`)
      setConnectorId(null)
      setView('installed')
      await refresh()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
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
      for (const field of fieldsFromSchema(selected.config_schema)) {
        const raw = config[field.key]
        parsedConfig[field.key] = field.type === 'integer' ? Number(raw) : raw
      }
      const result = await api.testConnection({ connector_id: selected.id, config: parsedConfig, secrets })
      setMsg(result.message || (result.ok ? 'Conexão validada.' : 'Não foi possível validar a conexão.'))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  async function onSync(id: string) {
    setBusy(true)
    setError(null)
    try {
      const result = await api.syncConnection(id)
      setMsg(`${result.status}: ${result.message}`)
      await refresh()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  async function onDelete(id: string) {
    setBusy(true)
    try {
      await api.deleteConnection(id)
      await refresh()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="connections-marketplace">
      <header className="connections-marketplace-head">
        <div>
          <div className="eyebrow">Integrações do Observa</div>
          <h1 className="page-title">Conexões</h1>
          <p className="page-sub">
            Adicione fontes de cloud, observabilidade, código, incidentes e ambientes privados.
          </p>
        </div>
        <div className="connections-security-note"><span aria-hidden="true" />Credenciais criptografadas</div>
      </header>

      <div className="connections-toolbar">
        <div className="connections-tabs" role="tablist" aria-label="Visualização de conexões">
          <button type="button" role="tab" aria-selected={view === 'catalog'} className={view === 'catalog' ? 'active' : ''} onClick={() => selectView('catalog')}>
            Catálogo <span>{connectors.length}</span>
          </button>
          <button type="button" role="tab" aria-selected={view === 'installed'} className={view === 'installed' ? 'active' : ''} onClick={() => selectView('installed')}>
            Instalados <span>{connections.length}</span>
          </button>
        </div>
        <label className="connections-search">
          <span aria-hidden="true">⌕</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={view === 'catalog' ? 'Buscar conectores…' : 'Buscar conexões instaladas…'}
            aria-label="Buscar conexões"
          />
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {msg && <p className="connections-message">{msg}</p>}

      <div className={`connections-browser ${view === 'installed' ? 'installed' : ''} ${selected ? 'with-detail' : ''}`}>
        {view === 'catalog' && <aside className="connections-filter" aria-label="Categorias de conectores">
          <div className="connections-filter-title">Categorias</div>
          <button type="button" className={category === 'all' ? 'active' : ''} onClick={() => setCategory('all')}>
            <span>Todos</span><b>{connectors.length}</b>
          </button>
          {CATEGORY_ORDER.filter((item) => categoryCounts[item]).map((item) => (
            <button key={item} type="button" className={category === item ? 'active' : ''} onClick={() => setCategory(item)}>
              <span>{CATEGORY_LABELS[item] || item}</span><b>{categoryCounts[item]}</b>
            </button>
          ))}
          <div className="connections-filter-foot">
            <span aria-hidden="true">●</span>
            Os conectores respeitam a company e tenancy ativas.
          </div>
        </aside>}

        <main className="connections-results">
          {view === 'catalog' ? (
            <>
              <div className="connections-results-head">
                <div><strong>Disponíveis</strong><span>{filteredConnectors.length} conectores encontrados</span></div>
                <span className="badge">Self-hosted</span>
              </div>
              {grouped.map(({ category: groupCategory, items }) => (
                <section key={groupCategory} className="connector-category">
                  <h2>{CATEGORY_LABELS[groupCategory] || groupCategory}</h2>
                  <div className="connector-grid">
                    {items.map((connector) => {
                      const installed = connections.some((connection) => connection.connector_id === connector.id)
                      return (
                        <article key={connector.id} className={`connector-plugin-card ${connector.id === connectorId ? 'selected' : ''}`}>
                          <div className="connector-plugin-top">
                            <ConnectorIcon icon={connector.icon} size={46} />
                            <div><strong>{connector.name}</strong><span>{CATEGORY_LABELS[connector.category] || connector.category}</span></div>
                            {installed && <span className="connector-installed-dot" title="Instalado" />}
                          </div>
                          <p>{connector.description}</p>
                          <div className="connector-plugin-capabilities">
                            {connector.capabilities.slice(0, 4).map((capability) => <span key={capability}>{capability}</span>)}
                          </div>
                          <button type="button" onClick={() => selectConnector(connector)}>
                            {installed ? 'Adicionar outra' : 'Configurar'} <span aria-hidden="true">→</span>
                          </button>
                        </article>
                      )
                    })}
                  </div>
                </section>
              ))}
              {filteredConnectors.length === 0 && <div className="connections-empty">Nenhum conector corresponde à busca.</div>}
            </>
          ) : (
            <>
              <div className="connections-results-head">
                <div><strong>Instalados</strong><span>{filteredConnections.length} conexões nesta tenancy</span></div>
                <button type="button" className="btn" onClick={() => selectView('catalog')}>Adicionar conexão</button>
              </div>
              <div className="installed-connections-grid">
                {filteredConnections.map((connection) => {
                  const connector = connectors.find((item) => item.id === connection.connector_id)
                  return (
                    <article className="installed-connection-card" key={connection.id}>
                      <ConnectorIcon icon={connector?.icon || 'generic'} size={42} />
                      <div className="installed-connection-copy">
                        <div><strong>{connection.name}</strong><span className={`badge ${connection.last_sync_status === 'ok' ? 'ok' : connection.last_sync_status ? 'fail' : ''}`}>{connection.last_sync_status || 'não sincronizado'}</span></div>
                        <p>{connector?.name || connection.connector_id}</p>
                        {connection.last_sync_message && <small>{connection.last_sync_message}</small>}
                      </div>
                      <div className="installed-connection-actions">
                        <button className="btn btn-primary" type="button" disabled={busy} onClick={() => onSync(connection.id)}>Sincronizar</button>
                        <button className="btn btn-danger" type="button" disabled={busy} onClick={() => onDelete(connection.id)}>Excluir</button>
                      </div>
                    </article>
                  )
                })}
              </div>
              {filteredConnections.length === 0 && <div className="connections-empty">Nenhuma conexão instalada corresponde à busca.</div>}
            </>
          )}
        </main>

        {selected && (
          <aside className="connector-detail" aria-label={`Configurar ${selected.name}`}>
            <div className="connector-detail-head">
              <ConnectorIcon icon={selected.icon} size={48} />
              <div><span>Configurar conector</span><h2>{selected.name}</h2></div>
              <button type="button" onClick={() => setConnectorId(null)} aria-label="Fechar configuração">×</button>
            </div>
            <p className="connector-detail-description">{selected.description}</p>
            <div className="connector-detail-privacy"><span aria-hidden="true">◆</span><div><strong>Escopo isolado</strong><p>Dados e credenciais ficam vinculados à tenancy ativa.</p></div></div>
            {selected.docs_url && <a className="connector-docs-link" href={selected.docs_url} target="_blank" rel="noreferrer">Onde obter as credenciais ↗</a>}
            <form className="form connector-detail-form" onSubmit={onCreate}>
              <label>Nome da conexão<input value={name} onChange={(event) => setName(event.target.value)} required /></label>
              {fieldsFromSchema(selected.config_schema).map((field) => (
                <label key={field.key}>{field.title}<input value={config[field.key] ?? ''} onChange={(event) => setConfig({ ...config, [field.key]: event.target.value })} /></label>
              ))}
              {fieldsFromSchema(selected.secrets_schema).map((field) => (
                <label key={field.key}>{field.title}<textarea value={secrets[field.key] ?? ''} onChange={(event) => setSecrets({ ...secrets, [field.key]: event.target.value })} placeholder="Armazenado criptografado e nunca exibido novamente" /></label>
              ))}
              <div className="connector-detail-actions">
                <button className="btn" type="button" onClick={onTest} disabled={busy}>Testar conexão</button>
                <button className="btn btn-primary" type="submit" disabled={busy}>Salvar conexão</button>
              </div>
            </form>
          </aside>
        )}
      </div>
    </div>
  )
}

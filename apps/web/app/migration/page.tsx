'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import {
  api,
  formatMoney,
  type MigrationCatalog,
  type MigrationComponent,
  type MigrationEstimate,
  type MigrationRequest,
  type MigrationScenario,
  type Product,
  type Resource,
} from '@/lib/api'

const PROVIDERS = { aws: 'AWS', gcp: 'Google Cloud', azure: 'Microsoft Azure' }

const INITIAL_COMPONENTS: MigrationComponent[] = [
  { name: 'Load balancer público', category: 'load_balancer', quantity: 1, usage: { hours: 730, processed_gb: 500 } },
  { name: 'API serverless', category: 'serverless_container', quantity: 1, usage: { vcpu: 2, memory_gb: 4, active_hours: 220, requests_million: 15, egress_gb: 80 } },
  { name: 'Bucket de arquivos', category: 'object_storage', quantity: 1, usage: { storage_gb: 750, operations_10k: 120, egress_gb: 90 } },
]

function errorMessage(cause: unknown) {
  if (!(cause instanceof Error)) return String(cause)
  try {
    const parsed = JSON.parse(cause.message)
    return parsed.detail || cause.message
  } catch {
    return cause.message
  }
}

export default function MigrationPage() {
  const [catalog, setCatalog] = useState<MigrationCatalog | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [resources, setResources] = useState<Resource[]>([])
  const [scenarios, setScenarios] = useState<MigrationScenario[]>([])
  const [scopeType, setScopeType] = useState<MigrationRequest['scope_type']>('custom')
  const [scopeValue, setScopeValue] = useState('')
  const [targets, setTargets] = useState(['aws', 'gcp', 'azure'])
  const [currency, setCurrency] = useState<'BRL' | 'USD'>('BRL')
  const [exchangeRate, setExchangeRate] = useState(5)
  const [commitment, setCommitment] = useState<0 | 12 | 36>(0)
  const [components, setComponents] = useState(INITIAL_COMPONENTS)
  const [usageDrafts, setUsageDrafts] = useState(INITIAL_COMPONENTS.map((row) => JSON.stringify(row.usage, null, 2)))
  const [result, setResult] = useState<MigrationEstimate | null>(null)
  const [scenarioName, setScenarioName] = useState('Arquitetura LB + API + bucket')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function refreshScenarios() {
    setScenarios(await api.migrationScenarios())
  }

  useEffect(() => {
    let active = true
    Promise.all([api.migrationCatalog(), api.products(), api.resources(), api.migrationScenarios()])
      .then(([catalogRow, productRows, resourceRows, scenarioRows]) => {
        if (!active) return
        setCatalog(catalogRow)
        setProducts(productRows)
        setResources(resourceRows)
        setScenarios(scenarioRows)
      })
      .catch((cause) => active && setError(errorMessage(cause)))
    return () => { active = false }
  }, [])

  const categoryOptions = useMemo(() => catalog?.providers[0]?.categories || [], [catalog])

  function buildRequest(): MigrationRequest {
    if (!targets.length) throw new Error('Selecione ao menos uma cloud de destino.')
    const parsedComponents = scopeType === 'custom' ? components.map((component, index) => {
      let usage: Record<string, number>
      try {
        usage = JSON.parse(usageDrafts[index] || '{}') as Record<string, number>
      } catch {
        throw new Error(`O consumo do componente “${component.name}” não é um JSON válido.`)
      }
      if (Object.values(usage).some((value) => typeof value !== 'number' || value < 0)) {
        throw new Error(`Todos os valores de consumo de “${component.name}” devem ser números positivos.`)
      }
      return { ...component, usage }
    }) : []
    if (scopeType !== 'custom' && !scopeValue) throw new Error('Selecione ou informe o valor do escopo.')
    return {
      scope_type: scopeType,
      scope_value: scopeType === 'custom' ? null : scopeValue,
      target_providers: targets,
      currency,
      usd_to_brl: exchangeRate,
      commitment_months: commitment,
      components: parsedComponents,
    }
  }

  async function estimate(event?: FormEvent) {
    event?.preventDefault()
    setLoading(true)
    setError('')
    setMessage('')
    try {
      setResult(await api.migrationEstimate(buildRequest()))
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setLoading(false)
    }
  }

  async function saveScenario() {
    if (!scenarioName.trim()) return setError('Informe um nome para salvar o cenário.')
    setLoading(true)
    setError('')
    try {
      const created = await api.createMigrationScenario({ ...buildRequest(), name: scenarioName.trim() })
      setResult(created.result)
      setMessage('Cenário salvo com isolamento nesta tenancy.')
      await refreshScenarios()
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setLoading(false)
    }
  }

  function addComponent() {
    const category = categoryOptions[0]?.id || 'compute'
    const usage = catalog?.default_usage[category] || { quantity: 1, hours: 730 }
    setComponents((rows) => [...rows, { name: `Componente ${rows.length + 1}`, category, quantity: 1, usage }])
    setUsageDrafts((rows) => [...rows, JSON.stringify(usage, null, 2)])
  }

  function updateComponent(index: number, patch: Partial<MigrationComponent>) {
    setComponents((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row))
  }

  function changeCategory(index: number, category: string) {
    const usage = catalog?.default_usage[category] || {}
    updateComponent(index, { category, usage })
    setUsageDrafts((rows) => rows.map((row, rowIndex) => rowIndex === index ? JSON.stringify(usage, null, 2) : row))
  }

  function removeComponent(index: number) {
    setComponents((rows) => rows.filter((_, rowIndex) => rowIndex !== index))
    setUsageDrafts((rows) => rows.filter((_, rowIndex) => rowIndex !== index))
  }

  async function removeScenario(id: string) {
    try {
      await api.deleteMigrationScenario(id)
      await refreshScenarios()
    } catch (cause) {
      setError(errorMessage(cause))
    }
  }

  function loadScenario(scenario: MigrationScenario) {
    const request = scenario.request
    setScopeType(request.scope_type)
    setScopeValue(request.scope_value || '')
    setTargets(request.target_providers)
    setCurrency(request.currency)
    setExchangeRate(request.usd_to_brl)
    setCommitment(request.commitment_months)
    setComponents(request.components || [])
    setUsageDrafts((request.components || []).map((row) => JSON.stringify(row.usage, null, 2)))
    setScenarioName(scenario.name)
    setResult(scenario.result)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="migration-page">
      <header className="migration-hero">
        <div>
          <span className="migration-eyebrow">FinOps · planejamento de migração</span>
          <h1 className="page-title">Simulador de custo multicloud</h1>
          <p className="page-sub">Compare recursos, contas, produtos ou arquiteturas completas entre AWS, Google Cloud e Azure.</p>
        </div>
        <div className="migration-reference"><strong>{catalog?.version || 'Carregando catálogo…'}</strong><span>estimativa de referência, não cotação oficial</span></div>
      </header>

      {message && <div className="demo-banner">{message}</div>}
      {error && <div className="migration-error">{error}</div>}

      <form className="migration-layout" onSubmit={estimate}>
        <section className="card migration-config">
          <div className="migration-section-head"><div><span className="step">01</span><h2>Defina o workload</h2></div></div>
          <div className="migration-scope-tabs">
            {(['resource', 'product', 'account', 'custom'] as const).map((scope) => (
              <button key={scope} type="button" className={scopeType === scope ? 'active' : ''} onClick={() => setScopeType(scope)}>
                {{ resource: 'Recurso', product: 'Produto', account: 'Conta / cloud', custom: 'Arquitetura' }[scope]}
              </button>
            ))}
          </div>

          {scopeType === 'product' && <label className="migration-field">Produto<select value={scopeValue} onChange={(event) => setScopeValue(event.target.value)} required>
            <option value="">Selecione um produto</option>{products.map((row) => <option key={row.slug} value={row.slug}>{row.name || row.slug} · {row.resource_count} recursos</option>)}
          </select></label>}
          {scopeType === 'resource' && <label className="migration-field">Recurso<select value={scopeValue} onChange={(event) => setScopeValue(event.target.value)} required>
            <option value="">Selecione um recurso</option>{resources.map((row) => <option key={row.uid} value={row.uid}>{row.name || row.id} · {row.provider} · {row.type}</option>)}
          </select></label>}
          {scopeType === 'account' && <label className="migration-field">Conta, projeto, subscription ou provider<input value={scopeValue} onChange={(event) => setScopeValue(event.target.value)} placeholder="all, aws, gcp, account-id ou project-id" required /></label>}

          {scopeType === 'custom' && <div className="migration-components">
            {components.map((component, index) => <article className="migration-component" key={`${component.name}-${index}`}>
              <div className="migration-component-head"><strong>Componente {index + 1}</strong><button type="button" onClick={() => removeComponent(index)}>Remover</button></div>
              <div className="migration-component-grid">
                <label>Nome<input value={component.name} onChange={(event) => updateComponent(index, { name: event.target.value })} /></label>
                <label>Tipo<select value={component.category} onChange={(event) => changeCategory(index, event.target.value)}>{categoryOptions.map((category) => <option key={category.id} value={category.id}>{category.label}</option>)}</select></label>
                <label className="migration-usage">Consumo mensal em JSON<textarea spellCheck={false} value={usageDrafts[index]} onChange={(event) => setUsageDrafts((rows) => rows.map((row, rowIndex) => rowIndex === index ? event.target.value : row))} /></label>
              </div>
            </article>)}
            <button className="btn" type="button" onClick={addComponent}>+ Adicionar componente</button>
          </div>}
        </section>

        <aside className="card migration-options">
          <div className="migration-section-head"><div><span className="step">02</span><h2>Premissas</h2></div></div>
          <fieldset><legend>Clouds de destino</legend>{Object.entries(PROVIDERS).map(([provider, label]) => <label className="migration-check" key={provider}><input type="checkbox" checked={targets.includes(provider)} onChange={(event) => setTargets((rows) => event.target.checked ? [...rows, provider] : rows.filter((row) => row !== provider))} /><span className={`provider-dot ${provider}`} />{label}</label>)}</fieldset>
          <label className="migration-field">Moeda<select value={currency} onChange={(event) => setCurrency(event.target.value as 'BRL' | 'USD')}><option value="BRL">BRL</option><option value="USD">USD</option></select></label>
          <label className="migration-field">Câmbio USD → BRL<input type="number" min="0.01" step="0.01" value={exchangeRate} onChange={(event) => setExchangeRate(Number(event.target.value))} /></label>
          <label className="migration-field">Compromisso<select value={commitment} onChange={(event) => setCommitment(Number(event.target.value) as 0 | 12 | 36)}><option value={0}>Sob demanda</option><option value={12}>12 meses</option><option value={36}>36 meses</option></select></label>
          <button className="btn btn-primary migration-submit" type="submit" disabled={loading}>{loading ? 'Calculando…' : 'Comparar custos'}</button>
          <div className="migration-save"><input value={scenarioName} onChange={(event) => setScenarioName(event.target.value)} placeholder="Nome do cenário" /><button className="btn" type="button" onClick={saveScenario} disabled={loading}>Salvar cenário</button></div>
          <p className="migration-note">Nenhuma migração ou alteração de infraestrutura é executada por esta tela.</p>
        </aside>
      </form>

      {result && <section className="migration-results">
        <div className="migration-result-head"><div><span className="migration-eyebrow">Resultado mensal estimado</span><h2>{result.components.length} componente(s) comparado(s)</h2></div><div className="migration-confidence">Confiança dos dados <strong>{Math.round(result.confidence * 100)}%</strong></div></div>
        <div className="migration-cloud-grid">{result.comparisons.map((comparison, index) => <article className={`migration-cloud card ${index === 0 ? 'winner' : ''}`} key={comparison.provider}>
          <div className="migration-cloud-title"><div><span className={`provider-dot ${comparison.provider}`} /><strong>{PROVIDERS[comparison.provider as keyof typeof PROVIDERS]}</strong></div>{index === 0 && <span className="badge ok">menor estimativa</span>}</div>
          <div className="migration-price">{formatMoney(comparison.monthly_cost, comparison.currency)}<small>/ mês</small></div>
          {comparison.savings_pct_vs_observed !== null && comparison.savings_pct_vs_observed !== undefined && <div className={comparison.savings_pct_vs_observed >= 0 ? 'migration-saving' : 'migration-extra'}>{comparison.savings_pct_vs_observed >= 0 ? 'Economia' : 'Acréscimo'} de {Math.abs(comparison.savings_pct_vs_observed)}% vs. observado</div>}
          <div className="migration-service-list">{comparison.services.map((service) => <details key={`${service.component}-${service.service}`}><summary><span><strong>{service.component}</strong><small>{service.service} · {service.sku}</small></span><b>US$ {service.monthly_usd.toFixed(2)}</b></summary><div className="migration-formulas">{service.lines.map((line) => <div key={line.metric}><span>{line.metric}</span><code>{line.formula} = US$ {line.amount_usd.toFixed(2)}</code></div>)}</div></details>)}</div>
        </article>)}</div>
        <div className="migration-warnings card"><strong>Premissas e limites</strong><ul>{result.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>
      </section>}

      <section className="card migration-history">
        <div className="migration-section-head"><div><span className="step">03</span><h2>Cenários salvos nesta tenancy</h2></div><span className="badge">{scenarios.length}</span></div>
        {scenarios.length === 0 ? <p className="muted">Nenhum cenário salvo.</p> : <div className="table-wrap"><table className="table"><thead><tr><th>Nome</th><th>Escopo</th><th>Menor custo</th><th>Catálogo</th><th>Criado em</th><th /></tr></thead><tbody>{scenarios.map((scenario) => <tr key={scenario.id}><td><button className="migration-link" type="button" onClick={() => loadScenario(scenario)}>{scenario.name}</button></td><td>{scenario.scope_type} {scenario.scope_value || ''}</td><td>{PROVIDERS[scenario.result.cheapest_provider as keyof typeof PROVIDERS]} · {formatMoney(scenario.result.comparisons[0].monthly_cost, scenario.currency)}</td><td>{scenario.catalog_version}</td><td>{new Date(scenario.created_at).toLocaleString('pt-BR')}</td><td><button className="btn-danger" type="button" onClick={() => removeScenario(scenario.id)}>Excluir</button></td></tr>)}</tbody></table></div>}
      </section>
    </div>
  )
}

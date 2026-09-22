'use client'

import { FormEvent, useEffect, useState } from 'react'
import { api, formatMoney, type BudgetEvent, type BudgetRule } from '@/lib/api'

export default function BudgetsPage() {
  const [rules, setRules] = useState<BudgetRule[]>([])
  const [events, setEvents] = useState<BudgetEvent[]>([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function refresh() {
    const [ruleRows, eventRows] = await Promise.all([api.budgets(), api.budgetEvents()])
    setRules(ruleRows)
    setEvents(eventRows)
  }

  useEffect(() => {
    let active = true
    Promise.all([api.budgets(), api.budgetEvents()])
      .then(([ruleRows, eventRows]) => {
        if (!active) return
        setRules(ruleRows)
        setEvents(eventRows)
      })
      .catch((cause) => active && setError(cause instanceof Error ? cause.message : String(cause)))
    return () => { active = false }
  }, [])

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    setError('')
    try {
      await api.createBudget({
        name: String(data.get('name')),
        scope_type: String(data.get('scope_type')),
        scope_value: String(data.get('scope_value')),
        amount: Number(data.get('amount')),
        currency: String(data.get('currency')),
        window_days: Number(data.get('window_days')),
        warning_threshold: Number(data.get('warning_threshold')) / 100,
        critical_threshold: Number(data.get('critical_threshold')) / 100,
        response_mode: String(data.get('response_mode')) as BudgetRule['response_mode'],
        owner: String(data.get('owner')) || null,
        resource_ids: String(data.get('resource_ids') || '')
          .split(',').map((value) => Number(value.trim())).filter(Boolean),
        dry_run: true,
        enabled: true,
      })
      setMessage('Budget criado em dry-run. Execute a avaliação para calcular consumo e forecast.')
      form.reset()
      await refresh()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    }
  }

  async function evaluate() {
    setLoading(true)
    setError('')
    try {
      const result = await api.monitorBudgets()
      setMessage(
        `${result.synced.length} conexão(ões) sincronizada(s); ` +
        `${result.evaluation.count} novo(s) evento(s).`,
      )
      await refresh()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setLoading(false)
    }
  }

  async function remove(id: string) {
    await api.deleteBudget(id)
    await refresh()
  }

  return (
    <div>
      <div className="alert-item-head">
        <div>
          <h1 className="page-title">Budgets e guardrails</h1>
          <p className="page-sub">Monitore custo real e projetado e envie desligamentos para aprovação.</p>
        </div>
        <button className="btn btn-primary" onClick={evaluate} disabled={loading}>
          {loading ? 'Monitorando…' : 'Sincronizar e avaliar'}
        </button>
      </div>
      {message && <div className="demo-banner">{message}</div>}
      {error && <p className="error">{error}</p>}

      <div className="grid grid-3">
        <section className="card">
          <h2>Novo budget</h2>
          <form className="form governance-form" onSubmit={create}>
            <label>Nome<input name="name" required placeholder="Budget checkout" /></label>
            <label>Escopo<select name="scope_type" defaultValue="product">
              <option value="product">Produto</option><option value="project">Projeto/conta</option>
              <option value="resource">Recurso</option><option value="provider">Provider</option>
            </select></label>
            <label>Valor do escopo<input name="scope_value" required placeholder="checkout" /></label>
            <div className="row">
              <label>Budget<input name="amount" type="number" min="0.01" step="0.01" required /></label>
              <label>Moeda<input name="currency" defaultValue="BRL" /></label>
            </div>
            <label>Janela em dias<input name="window_days" type="number" min="1" max="366" defaultValue="30" /></label>
            <div className="row">
            <label>Iniciar proteção %<input name="warning_threshold" type="number" defaultValue="80" /></label>
              <label>Crítico %<input name="critical_threshold" type="number" defaultValue="100" /></label>
            </div>
            <label>Resposta<select name="response_mode" defaultValue="notify">
              <option value="notify">Notificar</option><option value="approval">Solicitar desligamento</option>
              <option value="ignore">Ignorar</option>
            </select></label>
            <label>Owner<input name="owner" placeholder="squad ou e-mail; obrigatório para aprovação" /></label>
            <label>UIDs dos recursos<input name="resource_ids" placeholder="12, 15, 18" /></label>
            <button className="btn btn-primary" type="submit">Criar budget seguro</button>
          </form>
        </section>

        <section className="card budget-rules">
          <h2>Regras configuradas</h2>
          {rules.map((rule) => <div className="budget-item" key={rule.id}>
            <div className="alert-item-head"><strong>{rule.name}</strong><span className="badge">{rule.response_mode}</span></div>
            <div className="muted">{rule.scope_type}: {rule.scope_value}</div>
            <div className="value">{formatMoney(rule.amount, rule.currency)}</div>
            <div className="muted">{rule.window_days} dias · alerta {rule.warning_threshold * 100}% · crítico {rule.critical_threshold * 100}%</div>
            <div className="row"><span className="badge medium">dry-run</span><button className="btn-danger" onClick={() => remove(rule.id)}>Excluir</button></div>
          </div>)}
          {rules.length === 0 && <p className="muted">Nenhum budget configurado.</p>}
        </section>

        <section className="card budget-events">
          <h2>Eventos recentes</h2>
          {events.map((event) => <div className="budget-item" key={event.id}>
            <div className="alert-item-head"><strong>{event.level}</strong><span className="badge">{event.status}</span></div>
            <div className="muted">Real {formatMoney(event.actual_cost)} · projetado {formatMoney(event.projected_cost)}</div>
            <div className="value">{(event.usage_pct * 100).toFixed(1)}%</div>
            <div className="muted">{event.period_start} → {event.period_end}</div>
          </div>)}
          {events.length === 0 && <p className="muted">Nenhum limite atingido.</p>}
        </section>
      </div>
    </div>
  )
}

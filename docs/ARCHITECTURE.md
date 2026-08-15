# Observa — Architecture

## Goal

Self-hosted platform: **catalog + cost + observability signals** fed by **user-configured connectors**, with **SSO configured in the UI**.

## Layers

| Layer | Role |
|-------|------|
| **Web** | Setup wizard, Connections, Auth settings, Catalog, Costs, Health |
| **API core** | Org settings, RBAC, connection registry, sync orchestrator, query APIs |
| **Contracts** | Versioned signal schemas (`observa.*.v1`) |
| **Connectors** | Plugins: `test`, `pull`, `capabilities` |
| **Store** | SQLite locally (`data/observa.db`); Postgres later |

## Data flow

```
UI (Connections form)
  → POST /api/connections
  → encrypted secrets in SQLite
  → Sync worker runs connector.pull()
  → normalize to observa.cost.v1 / resource.v1 / metric.v1
  → Overview / Products / Alerts
```

## Auth

Stored in `settings` table (UI editable):

- `mode`: `local` | `oidc`
- OIDC providers: GitLab, Google (client id/secret/issuer/redirect)

Local mode: open access for MVP (single-user laptop). OIDC enforced when enabled.

## Non-goals (MVP)

- Full Datadog replacement (logs/traces search)
- Multi-tenant SaaS billing
- Shipping agents to every node (Prometheus/OTLP push comes later)

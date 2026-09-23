# Observa — Architecture

## Goal

Self-hosted platform: **catalog + cost + observability signals** fed by **user-configured connectors**, with **SSO configured in the UI**.

## Layers

| Layer | Role |
|-------|------|
| **Web** | Setup wizard, Connections, Auth settings, Catalog, Costs, Health |
| **API core** | Company/tenancy context, org settings, connection registry, sync orchestrator, query APIs |
| **Contracts** | Versioned signal schemas (`observa.*.v1`) |
| **Connectors** | Built-ins and `observa.connectors` plugins: `test`, `pull`, `capabilities` |
| **Store** | Control catalog plus one isolated SQLite database per tenancy; Postgres for horizontal scale |

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

## Portability

- Local workstation or bare metal through Python/Node or Docker Compose.
- Any VM through the same OCI images.
- Kubernetes through `deploy/kubernetes/observa.yaml`.
- Any cloud, cluster, SaaS or private environment through built-in, generic HTTP or plugin connectors.

## Non-goals (current version)

- Full Datadog replacement (logs/traces search)
- Cross-company billing of the Observa platform itself
- Shipping agents to every node (Prometheus/OTLP push comes later)

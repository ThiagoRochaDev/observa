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
| **Topology view** | Tenant-scoped ecosystem query, Dagre layout, React Flow rendering and local contextual analysis |

## Data flow

```
UI (Connections form)
  → POST /api/connections
  → encrypted secrets in SQLite
  → Sync worker runs connector.pull()
  → normalize to observa.cost.v1 / resource.v1 / metric.v1
  → Overview / Products / Alerts
```

### Mapa Vivo flow

```text
Active company + tenancy + selected product
  → GET /api/ecosystem?product=<slug>
  → authenticated, tenant-scoped topology query
  → normalized nodes + directed edges
  → Dagre left-to-right layout in the browser
  → React Flow canvas + component inspector
  → local contextual assistant (no external AI call by default)
```

The current endpoint uses showcase payloads from `demo_platform.py`. The production path must replace
that provider with persisted connector data filtered by authorized company and tenancy. See
[`MAPA_VIVO.md`](MAPA_VIVO.md) for the contract and migration criteria.

## Auth

Stored in `settings` table (UI editable):

- `mode`: `local` | `oidc`
- OIDC providers: GitLab, Google (client id/secret/issuer/redirect)

Local mode: a generated API key is required on every `/api` request and is validated before the
protected web shell is displayed. OIDC identity and company membership are enforced when OIDC is
enabled. Company and tenancy authorization remains a backend responsibility in both modes.

## Portability

- Local workstation or bare metal through Python/Node or Docker Compose.
- Any VM through the same OCI images.
- Kubernetes through `deploy/kubernetes/observa.yaml`.
- Any cloud, cluster, SaaS or private environment through built-in, generic HTTP or plugin connectors.

## Non-goals (current version)

- Full Datadog replacement (logs/traces search)
- Cross-company billing of the Observa platform itself
- Shipping agents to every node (Prometheus/OTLP push comes later)

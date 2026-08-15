# Connectors

Every data source in Observa — cloud, observability tool, incident manager,
VCS/CI, or an on-premise system — is a **connector**. All of them are
configured entirely in the UI (**Connections**): pick the tool, paste its
API key / PAT / token, test, save, sync. No env files, no redeploys.

## Interface

Every connector implements (`packages/connectors/observa_connectors/base.py`):

- `id` / `name` / `description`
- `category`: `cloud` | `observability` | `incident` | `vcs_cicd` | `on_prem` | `saas` | `demo`
- `icon`: slug the web UI maps to a colored badge (`apps/web/lib/api.ts` → `CONNECTOR_ICONS`)
- `docs_url`: where the client generates their credential
- `capabilities`: `cost`, `inventory`, `metrics`, …
- `config_schema` / `secrets_schema`: JSON Schema that renders the credential form automatically
- `test_connection(config, secrets) -> ok | error`
- `pull(config, secrets, since) -> PullResult` (costs, resources, metrics)

Credentials are encrypted at rest (Fernet, `app/core/crypto.py`) — never logged, never returned by the API.

## Registering a new connector

1. Add a module under `packages/connectors/observa_connectors/providers/` (or extend `stubs.py` for a schema-only placeholder).
2. Subclass `BaseConnector`, fill in `category` / `icon` / `docs_url` / schemas.
3. Implement `test_connection` and `pull` — use `observa_connectors.http.request_json` for REST APIs.
4. Register the instance in `registry.py`.

## Catalog

### Cloud
| ID | Status | Auth |
|----|--------|------|
| `aws-cost` | **Live** — Cost Explorer + EC2 inventory | Access key / secret key |
| `gcp-billing` | **Live** — BigQuery billing export | Service account JSON / ADC |
| `azure-cost` | **Live** — Cost Management Query API | Service principal (tenant/client/secret) |
| `digitalocean` | **Live** — droplets + balance | PAT |
| `vercel` | **Live** — projects | Access token |
| `mongodb-atlas` | **Live** — clusters | Public/private API key |
| `cloudflare` | **Live** — zones | API token |
| `oci` | Stub | API signing key |
| `linode` | Stub | PAT |
| `netlify` | Stub | PAT |

### Observability & APM
| ID | Status | Auth |
|----|--------|------|
| `datadog` | **Live** — usage cost, hosts, monitors | API key + App key |
| `newrelic` | **Live** — applications | User API key |
| `sentry` | **Live** — projects | Auth token |
| `grafana-cloud` | Stub | Access policy token |
| `elastic-cloud` | Stub | API key |

### Incident management
| ID | Status | Auth |
|----|--------|------|
| `pagerduty` | **Live** — services + triggered incidents | API token |
| `opsgenie` | Stub | API key |

### Source control & CI/CD
| ID | Status | Auth |
|----|--------|------|
| `github` | **Live** — repos + Actions minutes | PAT |
| `gitlab` | **Live** — projects | PAT |
| `bitbucket` | Stub | App password |

### On-premise & self-hosted
| ID | Status | Auth |
|----|--------|------|
| `kubernetes` | **Live** — node/pod inventory, any cluster (on-prem, EKS/GKE/AKS, k3s) | ServiceAccount bearer token |
| `prometheus` | **Live** — PromQL queries against any Prometheus/Thanos/Mimir | Bearer token or basic auth (optional) |
| `onprem-custom` | **Live** — generic HTTP polling for in-house tools | Bearer token / custom header |
| `splunk` | Stub | Auth token |

### Billing & data SaaS
| ID | Status | Auth |
|----|--------|------|
| `stripe` | **Live** — balance + charges | Secret key |
| `snowflake` | Stub | Key-pair (private key) |

### Demo
| ID | Status |
|----|--------|
| `mock-demo` | Ships a full synthetic dataset — cost, products, APM, alerts — for exploring the UI without any credentials |

"Stub" connectors already appear in the catalog with a working credential
form (so a client can save the connection and see it listed) — `pull()`
raises `NotImplementedError` until wired up. Swap `_StubConnector` for a real
`BaseConnector` implementation the same way `providers/saas.py` does.

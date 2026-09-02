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
| `oci` | **Live** — usage cost + resource inventory | API signing key (request signing) |
| `linode` | **Live** — instances + account balance | PAT |
| `netlify` | **Live** — sites + build minutes | PAT |

### Observability & APM
| ID | Status | Auth |
|----|--------|------|
| `datadog` | **Live** — usage cost, hosts, monitors | API key + App key |
| `newrelic` | **Live** — applications | User API key |
| `sentry` | **Live** — projects | Auth token |
| `grafana-cloud` | **Live** — stacks | Access policy token |
| `elastic-cloud` | **Live** — deployments | API key |

### Incident management
| ID | Status | Auth |
|----|--------|------|
| `pagerduty` | **Live** — services + triggered incidents | API token |
| `opsgenie` | **Live** — alerts + schedules | API key |

### Source control & CI/CD
| ID | Status | Auth |
|----|--------|------|
| `github` | **Live** — repos + Actions minutes | PAT |
| `gitlab` | **Live** — projects | PAT |
| `bitbucket` | **Live** — repos | App password |

### On-premise & self-hosted
| ID | Status | Auth |
|----|--------|------|
| `kubernetes` | **Live** — node/pod inventory, any cluster (on-prem, EKS/GKE/AKS, k3s) | ServiceAccount bearer token |
| `prometheus` | **Live** — PromQL queries against any Prometheus/Thanos/Mimir | Bearer token or basic auth (optional) |
| `onprem-custom` | **Live** — generic HTTP polling for in-house tools | Bearer token / custom header |
| `splunk` | **Live** — index volume + license usage | Auth token |

### Billing & data SaaS
| ID | Status | Auth |
|----|--------|------|
| `stripe` | **Live** — balance + charges | Secret key |
| `snowflake` | **Live** — warehouse credits + inventory | Key-pair (private key) |

### Demo
| ID | Status |
|----|--------|
| `mock-demo` | Ships a full synthetic dataset — cost, products, APM, alerts — for exploring the UI without any credentials |

All 27 connectors in the catalog are now **Live** — each `pull()` calls the
real vendor API. `oci` and `snowflake` sign the request/JWT with the
credential's private key (request signing / key-pair auth) instead of a
plain token, and need the optional `cryptography` dependency (`pip install
observa-connectors[oci]` / `[snowflake]`, or `[all]`).

New connector without a live vendor account to test against yet? Add a
`_StubConnector` subclass (schema-only placeholder, `pull()` raises
`NotImplementedError`) the same way the 9 above started out, then swap it
for a real `BaseConnector` implementation once you're ready — see
`providers/saas.py` for the pattern.

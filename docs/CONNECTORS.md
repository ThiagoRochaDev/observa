# Connectors

Every data source in Observa — cloud, observability tool, incident manager,
VCS/CI, or an on-premise system — is a **connector**. All of them are
configured entirely in the UI (**Connections**): pick the tool, paste its
API key / PAT / token, test, save, sync. No env files, no redeploys.

## Interface

Every connector implements (`packages/connectors/observa_connectors/base.py`):

- `id` / `name` / `description`
- `category`: `cloud` | `observability` | `incident` | `vcs_cicd` | `automation` | `database` | `data` | `security` | `collaboration` | `on_prem` | `saas` | `demo`
- `availability`: `native` (provider API) or `adapter` (customer-managed canonical API)
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

External packages do not need to change Observa's repository. Publish the connector
through Python's entry-point mechanism and install it in the API image/environment:

```toml
[project.entry-points."observa.connectors"]
my-tool = "my_observa_connector:MyToolConnector"
```

The registry discovers entry points at runtime. A plugin may expose one `BaseConnector`
instance/class or a list of instances; duplicate IDs never override built-in connectors.

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

### Automation and MCP
| ID | Status | Auth |
|----|--------|------|
| `mcp` | **Live** — `tools/list` discovery + configurable `tools/call` ingestion | Optional bearer token |

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

All 28 native connectors in the catalog are **Live** — each `pull()` calls the
real vendor API. `oci` and `snowflake` sign the request/JWT with the
credential's private key (request signing / key-pair auth) instead of a
plain token, and need the optional `cryptography` dependency (`pip install
observa-connectors[oci]` / `[snowflake]`, or `[all]`). GitHub is a native connector and supports
repository inventory plus Actions usage through an organization PAT.

## Extended adapter catalog

Observa also ships 80 catalog entries for tools such as OpenTelemetry, Dynatrace, Loki, Jaeger,
ServiceNow, Slack, Azure DevOps, Jenkins, Argo CD, Terraform Cloud, PostgreSQL, Redis, Kafka,
Databricks, Wiz, Okta, SonarQube and Snyk. The complete manifest lives in
`packages/connectors/observa_connectors/catalog.py`.

These entries are marked **Via API Adapter**, never **Native**. Each one is operational when the
customer provides an adapter URL implementing:

- `GET /health`: HTTP 2xx when credentials and upstream access are ready;
- `GET /observa/pull`: JSON object containing optional `costs`, `resources`, `metrics`, `logs` and
  `message` fields using the types in `observa_connectors.base`;
- optional bearer authentication configured and encrypted in the Observa connection form;
- optional `since=YYYY-MM-DD` query parameter for incremental synchronization.

The adapter runs in the customer's network and can call a paid SaaS API, an open-source tool, a
legacy service or an internal platform. This keeps vendor-specific credentials and transformations
under customer control while preserving the same tenancy isolation and normalized Observa signals.

## MCP connector

The native `mcp` connector supports the stateless `2026-07-28` Streamable HTTP protocol. It sends
the protocol version and routing headers on each request, discovers the configured tool with
`tools/list`, and invokes it with `tools/call`. The result must expose Observa canonical signals in
`structuredContent` or as JSON text content.

Configuration and secrets are tenancy-scoped:

- MCP endpoint URL and ingestion tool name;
- optional JSON arguments passed only to that tool;
- configurable protocol version for compatible servers;
- optional bearer token encrypted with the other connector credentials.

Use network allowlists for MCP egress and grant the token only the tools needed by Observa. The
connector never executes a tool other than the explicitly configured ingestion tool during sync.

For direct provider support, add a native `BaseConnector` implementation and switch the catalog
entry from adapter to native only after its credential test and pull behavior are covered by tests.

# Model Context Protocol (MCP)

Observa supports MCP in both directions:

1. **Observa as an MCP client** — configure the native MCP connector in **Connections** to call a
   remote tool and ingest canonical cost, resource, metric and log signals.
2. **Observa as an MCP server** — connect an AI assistant or automation platform to the protected
   `POST /mcp` endpoint and query the active tenancy using read-only tools.

## Observa as an MCP server

Endpoint:

```text
http://localhost:8080/mcp
```

The endpoint uses stateless MCP Streamable HTTP `2026-07-28`. Configure these headers in the MCP
client:

```text
Authorization: Bearer <OBSERVA_API_KEY_OR_OIDC_SESSION>
X-Observa-Company-ID: <COMPANY_ID>
X-Observa-Tenancy-ID: <TENANCY_ID>
```

The same authorization and membership checks used by `/api` protect `/mcp`. Omitting tenancy
headers selects the local default tenancy only when the authenticated identity is allowed to use it.

### Available tools

| Tool | Purpose |
|---|---|
| `observa_context` | Return the authorized company and tenancy |
| `observa_cost_summary` | Summarize costs by provider, product and squad |
| `observa_inventory` | List normalized infrastructure resources |
| `observa_products` | List product catalog entries and cost totals |
| `observa_alerts` | List recent cost and observability alerts |

All tools are read-only, idempotent and non-destructive. The MCP surface does not expose connector
secrets, API keys, encrypted values, remediation executors or approval mutations.

### Raw request example

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Authorization: Bearer $OBSERVA_API_KEY" \
  -H "X-Observa-Company-ID: $OBSERVA_COMPANY_ID" \
  -H "X-Observa-Tenancy-ID: $OBSERVA_TENANCY_ID" \
  -H "MCP-Protocol-Version: 2026-07-28" \
  -H "Mcp-Method: tools/call" \
  -H "Mcp-Name: observa_cost_summary" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"observa_cost_summary","arguments":{"days":30}}}'
```

For production, expose `/mcp` only through TLS, apply network allowlists, rotate credentials and
prefer a user/session token with membership only in the companies it needs to query.

## Observa as an MCP client

Open **Connections**, search for `MCP`, and configure:

- Streamable HTTP endpoint;
- ingestion tool name, default `observa_pull`;
- optional JSON arguments;
- protocol version;
- optional bearer token, encrypted at rest.

During testing, Observa calls `tools/list` and verifies the configured tool. During synchronization,
it calls only that tool using `tools/call`. The tool result must contain `structuredContent` or JSON
text with optional `costs`, `resources`, `metrics`, `logs` and `message` fields.

## Isolation guarantees

- Each MCP server request establishes company and tenancy context before database access.
- Database queries use the existing tenancy-scoped connection context.
- Remote MCP credentials belong to one saved connection in one tenancy.
- No remote MCP tool is called implicitly by the Observa server endpoint.
- Write actions remain outside MCP until an explicit approval-aware tool design is implemented.

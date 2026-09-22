# Budget guardrails

Observa can define cost limits for projects/accounts, products, providers and individual resources.
Each rule evaluates actual and projected spend over a configurable rolling window, which defaults
to 30 days.

## Origin and improvements

This design was informed by the legacy GCP projects `alert-budget-consume-manager` and
`budget-alert-shut-down`. Those projects provide useful Pub/Sub and Billing API patterns, but the
original flow also deletes and recreates budgets, depends on delayed BigQuery exports, infers the
project from a display name, and can detach project billing directly at a threshold.

Observa changes the control model:

- The configured budget is never raised automatically.
- Detection and remediation are separate stages.
- Repeated evaluations are deduplicated per rule, day and severity.
- Every event and decision is audited.
- Shutdown is represented as an action requiring approval.
- Approval is requested at the warning/protection threshold, before the fixed cap.
- Actions default to `dry_run`.
- `ignore` is explicit and still leaves a budget-event record.
- Owners are required when a rule can request shutdown.

## Rule model

| Field | Description |
|---|---|
| `scope_type` | `project`, `account`, `product`, `provider` or `resource` |
| `scope_value` | Identifier used to find matching cost records |
| `amount` | Maximum desired cost in the configured currency |
| `window_days` | Rolling evaluation window; default 30 |
| `warning_threshold` | Fraction that creates a warning; default 0.8 |
| `critical_threshold` | Fraction that creates a critical event; default 1.0 |
| `response_mode` | `notify`, `approval` or `ignore` |
| `owner` | Squad or user responsible for approval |
| `resource_ids` | Inventory UIDs eligible for shutdown |
| `dry_run` | Simulate provider actions when approved |

The evaluator calculates both actual spend and a projection:

```text
projected = actual / observed_days * window_days
usage_pct = max(actual, projected) / budget_amount
```

This detects fast cost growth before the full window has elapsed.

## Response modes

### Notify

Creates a budget event and an Observa alert. No infrastructure action is created.

### Approval

At the warning/protection threshold, Observa creates one pending `stop` action for each mapped
resource. The action appears in Governance, the mobile app and the CLI. It runs only after
approval and respects the rule's `dry_run` value. If the rule later becomes critical, Observa
reuses an existing pending action instead of creating approval spam.

### Ignore

Creates an event with status `ignored`, but does not create an alert or action. This allows an
owner to record an intentional exception without hiding the historical decision.

## Example

```json
{
  "name": "Checkout monthly guardrail",
  "scope_type": "product",
  "scope_value": "checkout",
  "amount": 5000,
  "currency": "BRL",
  "window_days": 30,
  "warning_threshold": 0.8,
  "critical_threshold": 1.0,
  "response_mode": "approval",
  "owner": "squad-checkout",
  "resource_ids": [12, 13],
  "dry_run": true,
  "enabled": true
}
```

Synchronize every enabled cost connector and then evaluate all rules:

```bash
curl -X POST http://localhost:8080/api/budgets/monitor \
  -H "X-Observa-Api-Key: $OBSERVA_API_KEY" \
  -H "Content-Type: application/json" -d '{}'
```

Run this endpoint periodically from cron, Kubernetes CronJob, Cloud Scheduler or EventBridge.

## Fixed-cap protection

Cloud billing data is not real-time, so no external FinOps tool can guarantee an exact monetary
cutoff after every cent. To reduce overrun risk, configure the protection threshold below 100%
(for example 70% or 80%), run `/api/budgets/monitor` frequently, map the affected resources, and
keep the approval owner reachable. Provider-native quotas and organization policies should be
used together with Observa for workloads that require a strict technical ceiling.

## Connector behavior

Budget detection works with normalized `cost_records`, independently of the source connector.
Approved shutdown depends on connector support:

- Mock Demo: complete simulated flow.
- AWS EC2: tag write-back and start/stop.
- GCP and Azure: cost detection works; resource mutation still requires provider-specific action
  adapters and inventory mapping.

Observa deliberately does not detach billing from an entire cloud project. Project-wide
remediation should stop mapped workloads or use a separately reviewed provider adapter with
organization-specific safeguards.

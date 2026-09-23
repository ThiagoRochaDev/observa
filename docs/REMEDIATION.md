# Log diagnosis and approved remediation

Observa can ingest logs from dedicated connectors or `POST /api/logs/ingest`, correlate repeated
application failures and generate remediation proposals inside the selected tenancy.

## Safety workflow

1. An operator connects a logging platform or pushes normalized `observa.log.v1` events.
2. `POST /api/remediations/analyze` scans only tenant-local logs.
3. Observa proposes a diagnosis, recommendation and sanitized action; nothing is executed.
4. An owner/admin approves or rejects the proposal.
5. Dry-run is the default and records `simulated` without calling another system.
6. A real correction requires both `dry_run=false` and a connector with a remediation executor.
7. The outcome is recorded as `successful`, `failed` or `false_positive`.

False-positive feedback suppresses the same fingerprint in that tenancy. Successful feedback
marks the recommendation as previously validated for that customer. Learning never crosses
company or tenancy boundaries.

## Generic private executor

The `onprem-custom` connector accepts an optional `remediation_url`. After explicit approval,
Observa POSTs only the proposal ID, title, diagnosis, recommendation and structured action to
that customer-controlled endpoint. It does not send raw logs, access tokens or connector secrets.
The endpoint can trigger the customer's own CI/CD, GitOps, runbook or incident workflow.

## Roles

- `viewer`: read proposals only.
- `operator`: ingest/analyze logs and submit feedback.
- `admin` / `owner`: approve or reject remediation.
- local platform API key: installation administrator; use only for bootstrap/emergency access.

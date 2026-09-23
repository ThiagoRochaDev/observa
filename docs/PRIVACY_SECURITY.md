# Privacy and tenant isolation

Observa is designed so one customer cannot discover or read another customer's data.

## Isolation guarantees

- Every tenancy has a separate SQLite database containing connections, encrypted secrets,
  costs, resources, metrics, logs, alerts, budgets, automation, remediations and audit data.
- The control database stores only company/tenancy metadata and explicit memberships.
- OIDC authentication does not grant data access by itself. The identity `subject` must be
  explicitly assigned to the company as `owner`, `admin`, `operator` or `viewer`.
- Company listings are filtered by membership. Selecting an unassigned tenancy returns 403.
- Viewers cannot create connections, sync, tag, automate, analyze or approve changes.
- Remediation approval requires `owner` or `admin`.
- Connector credentials use Fernet encryption and are never returned by the API.

The local API key is the installation's platform-administrator credential. Anyone holding it
can access every company, so keep it in a secret manager, never embed it in source code, rotate
it if exposed, and do not share it with ordinary users. Production users should authenticate
with OIDC and receive only the memberships they need.

## Data egress

Observa does not send logs, source code, credentials or customer metadata to an external AI
service by default. Log diagnosis runs inside the API process with deterministic local rules.
Only the selected tenancy database is queried.

Data leaves the installation only when an authorized operator configures a connector endpoint
and requests a test/sync, or when an owner/admin approves a non-dry-run remediation using a
configured executor. Remediation webhooks receive a sanitized proposal; raw logs and secrets
are not included.

External connector plugins execute inside the API trust boundary. Install only reviewed and
signed packages, pin versions and inspect their outbound destinations. Network policies should
allow egress only to approved provider and customer endpoints.

## Operational controls

- Put web/API behind TLS and an identity-aware reverse proxy.
- Back up and encrypt the entire `data` volume.
- Restrict filesystem access to the API process account.
- Use Kubernetes NetworkPolicy/firewall allowlists for connector egress.
- Never commit `data/`, `.env`, API keys, session secrets or connector credentials.
- Review `audit_events` after membership, automation and remediation operations.

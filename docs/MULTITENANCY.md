# Companies and tenancies

Observa separates the customer hierarchy into two levels:

- **Company**: the legal or business organization using Observa.
- **Tenancy**: an isolated operating environment inside a company, such as production,
  sandbox, a business unit, a country, or a managed customer.

A company may own any number of tenancies. Connections, encrypted credentials, costs,
resources, metrics, alerts, budgets, policies, approvals and audit events are physically
stored in a separate SQLite database for each tenancy.

## Request context

All data API calls accept these headers:

```text
X-Observa-Company-ID: cmp_...
X-Observa-Tenancy-ID: tnt_...
```

If omitted, Observa uses `cmp_default` and `tnt_default`, preserving compatibility with
existing installations. A company/tenancy mismatch returns HTTP 409, and unknown or
disabled tenancies return HTTP 404.

The web application stores the selected context locally and sends it on every request.
The CLI supports `--company-id`, `--tenancy-id`, `OBSERVA_COMPANY_ID` and
`OBSERVA_TENANCY_ID`. The mobile app stores both identifiers in Expo SecureStore.

## Management API

```http
GET  /api/companies
POST /api/companies
GET  /api/tenancies?company_id=cmp_...
POST /api/tenancies
GET  /api/context
```

The shared local API key acts as a platform administrator credential. OIDC users see only
companies where their immutable session subject has an explicit membership. Roles are
`owner`, `admin`, `operator` and `viewer`; viewers are read-only, and remediation approval
requires owner/admin. Protect the platform key in a secret manager and use it only to bootstrap
owners or recover the installation.

## Storage

```text
data/
├── observa_control.db       # companies and tenancies
├── observa.db               # backward-compatible default tenancy
└── tenancies/
    ├── tnt_abc....db
    └── tnt_xyz....db
```

Back up the complete `data` directory. Restoring only one tenancy database restores its
operational data, while `observa_control.db` preserves its company relationship.

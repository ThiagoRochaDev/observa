# Observa roadmap

## Done (local MVP)

- [x] Monorepo scaffold (`apps/api`, `apps/web`, `packages/connectors`)
- [x] UI: Connections (create / test / sync / delete)
- [x] UI: Authentication settings (GitLab + Google forms, stored in DB)
- [x] Mock Demo connector with cost + resources
- [x] Stub connectors: GCP Billing, AWS Cost, Azure Cost (forms only)
- [x] Overview + Products views
- [x] Encrypted secrets at rest (Fernet)

## Next

- [ ] OIDC login redirect flow (use saved GitLab/Google settings)
- [ ] Implement `gcp-billing` pull (BigQuery)
- [ ] Implement `aws-cost` / `azure-cost` pull
- [ ] Alert rules (cost anomaly)
- [ ] Prometheus / OTLP ingest connector
- [ ] Postgres option + Docker Compose production-ish

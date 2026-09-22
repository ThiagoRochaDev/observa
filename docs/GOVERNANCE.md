# Governance, tags and schedules

Observa centralizes cloud-resource metadata and controlled lifecycle actions. The API is the
single enforcement point used by the web app, CLI and mobile app.

## Safety model

- Tag and power operations default to `dry_run=true`.
- Policies default to `require_approval=true`.
- Every preview, mutation, approval and rejection is written to `audit_events`.
- A connector must explicitly implement `apply_tags` or `change_power_state`.
- AWS currently supports write-back and start/stop for EC2 instances.
- The mock connector supports the complete workflow without touching a cloud account.

## API examples

Apply an owner tag after previewing it:

```bash
curl -X PATCH http://localhost:8080/api/resources/1/tags \
  -H "X-Observa-Api-Key: $OBSERVA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tags":{"owner":"platform"},"dry_run":false,"write_back":true}'
```

Create a weekday schedule in Sao Paulo time:

```json
{
  "name": "Homologation business hours",
  "selector": {"environment": "staging"},
  "timezone": "America/Sao_Paulo",
  "weekdays": [0, 1, 2, 3, 4],
  "start_time": "07:00",
  "stop_time": "20:00",
  "require_approval": true,
  "dry_run": true
}
```

Call `POST /api/automation/run-due` once per minute from cron, Kubernetes CronJob or another
scheduler. Repeated calls for the same minute are idempotent.

## CLI

```bash
pip install -e apps/cli
export OBSERVA_URL=http://localhost:8080
export OBSERVA_API_KEY=your-key

observa resources --untagged
observa tag 12 --set owner=platform --set product=checkout
observa tag 12 --set owner=platform --apply
observa policies create "Staging business hours" --selector environment=staging \
  --timezone America/Sao_Paulo --start 07:00 --stop 20:00
observa actions list --status pending_approval
observa actions approve act_123
observa run-due
```

## Mobile

The Expo app lives in `apps/mobile`. It stores the API key with SecureStore and provides a
mobile cost summary, unmapped-resource list, pull-to-refresh, and approval/rejection actions.

```bash
cd apps/mobile
npm install
npm start
```

Android emulators reach a locally running API through `http://10.0.2.2:8080`. Physical devices
must use the machine's LAN address and a network policy that allows the API port.

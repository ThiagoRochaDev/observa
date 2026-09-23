# Observa product walkthrough

`observa-complete-walkthrough.mp4` demonstrates the web dashboard, organizations and tenancies,
cost and budget governance, log remediation, CLI, and mobile experience.

The video is generated from isolated browser frames. It never records the desktop and does not
embed API keys, credentials, customer payloads, or other local applications.

To regenerate it, start the API and web app with demo-only data, then run:

```powershell
$env:OBSERVA_DEMO_API_KEY = '<demo-only-key>'
.\.venv\Scripts\python scripts\capture_demo.py
```

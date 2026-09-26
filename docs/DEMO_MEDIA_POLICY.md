# Public demonstrations and media

All public screenshots, videos, examples and acceptance tests must use an isolated
Mock Demo instance with **synthetic data for TGR products only**: Move Easy,
Easy Food, Detect Easy, Observa and TGR VR & Archviz. Costs, graphs, services,
alerts and metrics are fictional and do not describe their production systems.

Never capture a customer, employer, partner or other third-party environment.
Do not use their names, internal product names, organization IDs, billing,
credentials, logs or operational screenshots, even with selected values blurred.
Provider names in the connector catalog document integrations, not customers or
endorsements. Do not remove required upstream license notices.

## Before publishing media

1. Create a fresh, disposable data directory. Never reuse an existing operator's
   database or connect a real provider for a public demonstration.
2. Use only Mock Demo and the five TGR products above. Label the material
   **Demonstração TGR — dados fictícios**.
3. Inspect every visible name, value, notification, URL and frame. Never display
   an API key, user e-mail, local username, organization ID or real resource name.
4. Run the API demo catalog tests. Have the owner review the resulting media
   before adding it to the README, docs, releases or marketing materials.
5. Record the dataset version, capture date and review in the media's accompanying
   documentation. Do not describe a mock-up as an actual app screenshot.

The previous screenshots and walkthrough were removed from the current source
tree. They must not be restored or reused. This removal does not erase Git
history, forks or copies. No replacement capture is approved merely because an
automated scan passed.

## Existing local demo data

Updating the code does not rename products already stored in an installation.
For new public media, start a fresh disposable directory containing only mock
data. Do not reset or delete an operator's existing database automatically.

Tests exercise the actual Observa API using the synthetic TGR catalog; they do
not connect to live TGR product infrastructure.

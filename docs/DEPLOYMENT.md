# Portable deployment

Observa is self-hosted and does not require a specific cloud. The API and web application
run as non-root containers and can be deployed locally, on a VM, in Kubernetes, or behind
an enterprise reverse proxy.

## Local workstation

```bash
docker compose up --build
```

Open `http://localhost:3000`. The API key is printed by the API container on first boot
and persisted in the `observa-data` volume.

## VM or bare metal

Install Docker Engine and Compose on the VM, clone the repository, configure firewall/TLS
at the reverse proxy, and run:

```bash
docker compose up -d --build
docker compose logs api
```

Persist `/data`, allow outbound HTTPS to every configured provider, and restrict inbound
access to the web/API ports or to the reverse proxy only.

## Kubernetes

Build and publish `observa-api` and `observa-web` images, replace the two `:local` image
references in `deploy/kubernetes/observa.yaml`, then run:

```bash
kubectl apply -f deploy/kubernetes/observa.yaml
kubectl -n observa port-forward service/observa-web 3000:3000
kubectl -n observa port-forward service/observa-api 8080:8080
kubectl -n observa logs deployment/observa-api
```

For production, add an Ingress/Gateway with TLS, network policies, PVC snapshots and a
single API replica while SQLite is used. Horizontal API scaling requires moving the store
to PostgreSQL and distributing sync jobs through a queue.

## Connecting any environment

Built-in connectors cover public clouds, Kubernetes, Prometheus, Splunk, Git providers,
APM tools, incident systems and SaaS billing. `onprem-custom` polls an arbitrary internal
HTTP endpoint, so private tools can emit Observa's normalized cost/resource/metric format.

Third parties can install Python packages exposing the entry-point group
`observa.connectors`:

```toml
[project.entry-points."observa.connectors"]
my-tool = "my_observa_connector:MyToolConnector"
```

The target class must extend `BaseConnector`. Installed plugins automatically appear in
the Connections catalog without changes to Observa's source code.

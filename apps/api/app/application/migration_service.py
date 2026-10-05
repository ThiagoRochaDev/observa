from __future__ import annotations

import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.core import db
from app.core.config import get_settings
from app.application import official_pricing_service

CATALOG_VERSION = "observa-reference-2026.10-v1"
SUPPORTED_PROVIDERS = ("aws", "gcp", "azure")

CATEGORY_LABELS = {
    "compute": "Máquina virtual / compute",
    "container_platform": "Kubernetes / plataforma de containers",
    "serverless_container": "Container serverless",
    "database": "Banco relacional gerenciado",
    "load_balancer": "Load balancer",
    "object_storage": "Object storage / bucket",
    "cache": "Cache gerenciado",
}

DEFAULT_USAGE: dict[str, dict[str, float]] = {
    "compute": {"quantity": 1, "vcpu": 2, "memory_gb": 8, "hours": 730, "storage_gb": 50, "egress_gb": 50},
    "container_platform": {"quantity": 1, "vcpu": 4, "memory_gb": 16, "hours": 730, "storage_gb": 100, "egress_gb": 100},
    "serverless_container": {"quantity": 1, "vcpu": 1, "memory_gb": 1, "active_hours": 180, "requests_million": 10, "egress_gb": 50},
    "database": {"quantity": 1, "vcpu": 4, "memory_gb": 16, "hours": 730, "storage_gb": 100, "backup_gb": 100, "egress_gb": 20},
    "load_balancer": {"quantity": 1, "hours": 730, "processed_gb": 500},
    "object_storage": {"quantity": 1, "storage_gb": 500, "operations_10k": 100, "egress_gb": 100},
    "cache": {"quantity": 1, "memory_gb": 4, "hours": 730, "egress_gb": 20},
}

RATE_CARDS: dict[str, dict[str, dict[str, Any]]] = {
    "aws": {
        "compute": {"service": "Amazon EC2", "sku": "reference.general-purpose", "rates": {"vcpu_hour": 0.0464, "memory_gb_hour": 0.0052, "storage_gb_month": 0.080, "egress_gb": 0.090}},
        "container_platform": {"service": "Amazon EKS + EC2", "sku": "reference.eks-managed", "rates": {"cluster_hour": 0.100, "vcpu_hour": 0.0464, "memory_gb_hour": 0.0052, "storage_gb_month": 0.080, "egress_gb": 0.090}},
        "serverless_container": {"service": "AWS Fargate / App Runner", "sku": "reference.serverless-container", "rates": {"vcpu_hour": 0.0405, "memory_gb_hour": 0.0045, "requests_million": 0.200, "egress_gb": 0.090}},
        "database": {"service": "Amazon RDS", "sku": "reference.relational-ha", "rates": {"vcpu_hour": 0.0520, "memory_gb_hour": 0.0120, "storage_gb_month": 0.115, "backup_gb_month": 0.095, "egress_gb": 0.090}},
        "load_balancer": {"service": "Elastic Load Balancing", "sku": "reference.application-lb", "rates": {"lb_hour": 0.0225, "processed_gb": 0.0080}},
        "object_storage": {"service": "Amazon S3", "sku": "reference.standard", "rates": {"storage_gb_month": 0.0230, "operations_10k": 0.050, "egress_gb": 0.090}},
        "cache": {"service": "Amazon ElastiCache", "sku": "reference.managed-cache", "rates": {"memory_gb_hour": 0.0240, "egress_gb": 0.010}},
    },
    "gcp": {
        "compute": {"service": "Compute Engine", "sku": "reference.e2-general-purpose", "rates": {"vcpu_hour": 0.0335, "memory_gb_hour": 0.0045, "storage_gb_month": 0.040, "egress_gb": 0.085}},
        "container_platform": {"service": "Google Kubernetes Engine", "sku": "reference.gke-standard", "rates": {"cluster_hour": 0.100, "vcpu_hour": 0.0335, "memory_gb_hour": 0.0045, "storage_gb_month": 0.040, "egress_gb": 0.085}},
        "serverless_container": {"service": "Cloud Run", "sku": "reference.cloud-run", "rates": {"vcpu_hour": 0.0864, "memory_gb_hour": 0.0090, "requests_million": 0.400, "egress_gb": 0.085}},
        "database": {"service": "Cloud SQL", "sku": "reference.custom-ha", "rates": {"vcpu_hour": 0.0413, "memory_gb_hour": 0.0070, "storage_gb_month": 0.170, "backup_gb_month": 0.080, "egress_gb": 0.085}},
        "load_balancer": {"service": "Cloud Load Balancing", "sku": "reference.external-managed", "rates": {"lb_hour": 0.0250, "processed_gb": 0.0080}},
        "object_storage": {"service": "Cloud Storage", "sku": "reference.standard-regional", "rates": {"storage_gb_month": 0.0200, "operations_10k": 0.050, "egress_gb": 0.085}},
        "cache": {"service": "Memorystore", "sku": "reference.standard-cache", "rates": {"memory_gb_hour": 0.0270, "egress_gb": 0.010}},
    },
    "azure": {
        "compute": {"service": "Azure Virtual Machines", "sku": "reference.dsv5-general-purpose", "rates": {"vcpu_hour": 0.0430, "memory_gb_hour": 0.0050, "storage_gb_month": 0.075, "egress_gb": 0.087}},
        "container_platform": {"service": "Azure Kubernetes Service", "sku": "reference.aks-managed", "rates": {"cluster_hour": 0.100, "vcpu_hour": 0.0430, "memory_gb_hour": 0.0050, "storage_gb_month": 0.075, "egress_gb": 0.087}},
        "serverless_container": {"service": "Azure Container Apps", "sku": "reference.container-apps", "rates": {"vcpu_hour": 0.0440, "memory_gb_hour": 0.0050, "requests_million": 0.400, "egress_gb": 0.087}},
        "database": {"service": "Azure Database", "sku": "reference.flexible-ha", "rates": {"vcpu_hour": 0.0500, "memory_gb_hour": 0.0090, "storage_gb_month": 0.120, "backup_gb_month": 0.090, "egress_gb": 0.087}},
        "load_balancer": {"service": "Azure Application Gateway / Load Balancer", "sku": "reference.standard", "rates": {"lb_hour": 0.0260, "processed_gb": 0.0085}},
        "object_storage": {"service": "Azure Blob Storage", "sku": "reference.hot-lrs", "rates": {"storage_gb_month": 0.0184, "operations_10k": 0.055, "egress_gb": 0.087}},
        "cache": {"service": "Azure Managed Redis", "sku": "reference.managed-cache", "rates": {"memory_gb_hour": 0.0260, "egress_gb": 0.010}},
    },
}

RESOURCE_ALIASES = {
    "cloud_run": "serverless_container",
    "app_runner": "serverless_container",
    "container_app": "serverless_container",
    "lambda": "serverless_container",
    "function": "serverless_container",
    "gke_deployment": "container_platform",
    "kubernetes": "container_platform",
    "eks": "container_platform",
    "aks": "container_platform",
    "cloudsql": "database",
    "rds": "database",
    "azure_sql": "database",
    "postgres": "database",
    "mysql": "database",
    "load_balancer": "load_balancer",
    "application_load_balancer": "load_balancer",
    "alb": "load_balancer",
    "bucket": "object_storage",
    "object_storage": "object_storage",
    "s3": "object_storage",
    "blob_storage": "object_storage",
    "elasticache": "cache",
    "memorystore": "cache",
    "redis": "cache",
    "vm": "compute",
    "instance": "compute",
    "compute_instance": "compute",
}


def catalog() -> dict[str, Any]:
    pricing_config = official_pricing_service.get_config()
    return {
        "version": CATALOG_VERSION,
        "currency": "USD",
        "kind": "reference",
        "notice": "Valores de referência para comparação arquitetural; importe catálogos oficiais e negociações privadas antes de decidir uma migração.",
        "providers": [
            {
                "id": provider,
                "name": {"aws": "AWS", "gcp": "Google Cloud", "azure": "Microsoft Azure"}[provider],
                "categories": [
                    {
                        "id": category,
                        "label": CATEGORY_LABELS[category],
                        "service": card["service"],
                        "sku": card["sku"],
                        "rates": card["rates"],
                    }
                    for category, card in RATE_CARDS[provider].items()
                ],
            }
            for provider in SUPPORTED_PROVIDERS
        ],
        "default_usage": DEFAULT_USAGE,
        "pricing": {
            "mode": pricing_config["mode"],
            "cache_hours": pricing_config["cache_hours"],
            "regions": pricing_config["regions"],
            "official_mappings_configured": {
                provider: bool(pricing_config["mappings"].get(provider)) for provider in SUPPORTED_PROVIDERS
            },
            "gcp_catalog_configured": pricing_config["gcp_catalog_configured"],
        },
    }


def _number(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed >= 0 else fallback


def _category(resource_type: str) -> str:
    normalized = resource_type.strip().lower().replace("-", "_")
    if normalized in RESOURCE_ALIASES:
        return RESOURCE_ALIASES[normalized]
    for token, category in RESOURCE_ALIASES.items():
        if token in normalized:
            return category
    return "compute"


def _usage_from_resource(resource: dict[str, Any]) -> tuple[dict[str, float], float, list[str]]:
    category = _category(str(resource.get("type") or "compute"))
    usage = deepcopy(DEFAULT_USAGE[category])
    labels = resource.get("labels") or {}
    aliases = {
        "cpu": "vcpu",
        "cpus": "vcpu",
        "memory": "memory_gb",
        "memory_gib": "memory_gb",
        "disk_gb": "storage_gb",
        "size_gb": "storage_gb",
        "monthly_hours": "hours",
        "requests": "requests_million",
        "requests_m": "requests_million",
        "network_egress_gb": "egress_gb",
    }
    explicit = 0
    for key, value in labels.items():
        usage_key = aliases.get(key, key)
        if usage_key in usage:
            usage[usage_key] = _number(value, usage[usage_key])
            explicit += 1
    tier = str(labels.get("tier") or "")
    tier_match = re.search(r"custom-(\d+)-(\d+)", tier)
    if tier_match and category == "database":
        usage["vcpu"] = float(tier_match.group(1))
        usage["memory_gb"] = round(float(tier_match.group(2)) / 1024, 2)
        explicit += 2
    confidence = min(0.9, 0.45 + explicit * 0.08)
    warnings = [] if explicit else ["Consumo não encontrado nos labels; foram usados defaults editáveis da categoria."]
    return usage, confidence, warnings


def _resource_component(resource: dict[str, Any]) -> dict[str, Any]:
    usage, confidence, warnings = _usage_from_resource(resource)
    return {
        "name": resource.get("name") or resource.get("id") or f"resource-{resource.get('uid')}",
        "category": _category(str(resource.get("type") or "compute")),
        "source_provider": resource.get("provider"),
        "source_service": resource.get("type"),
        "resource_uid": resource.get("uid"),
        "usage": usage,
        "confidence": confidence,
        "warnings": warnings,
    }


def _select_resources(scope_type: str, scope_value: str | None) -> list[dict[str, Any]]:
    if scope_type == "resource":
        try:
            resource_uid = int(scope_value or "")
        except ValueError as exc:
            raise ValueError("Resource scope requires a numeric resource UID") from exc
        resource = db.get_resource(resource_uid)
        if not resource:
            raise ValueError("Resource not found")
        return [resource]
    if scope_type == "product":
        if not scope_value:
            raise ValueError("Product scope requires a product slug")
        resources = db.list_resources(scope_value)
        if not resources:
            raise ValueError("No resources found for product")
        return resources
    if scope_type == "account":
        resources = db.list_resources()
        if not scope_value or scope_value.lower() in {"all", "*"}:
            return resources
        normalized = scope_value.lower()
        selected = [
            resource
            for resource in resources
            if str(resource.get("provider") or "").lower() == normalized
            or normalized
            in {
                str((resource.get("labels") or {}).get(key) or "").lower()
                for key in ("account", "account_id", "project", "project_id", "subscription")
            }
        ]
        if not selected:
            raise ValueError("No resources found for account/provider scope")
        return selected
    raise ValueError("Scope type must be resource, product, account or custom")


def _custom_components(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        raise ValueError("Custom scope requires at least one architecture component")
    components = []
    for index, row in enumerate(rows):
        category = str(row.get("category") or "")
        if category not in DEFAULT_USAGE:
            raise ValueError(f"Unsupported component category: {category}")
        usage = deepcopy(DEFAULT_USAGE[category])
        for key, value in (row.get("usage") or {}).items():
            if key in usage:
                usage[key] = _number(value, usage[key])
        usage["quantity"] = _number(row.get("quantity"), usage.get("quantity", 1))
        components.append(
            {
                "name": str(row.get("name") or f"component-{index + 1}"),
                "category": category,
                "source_provider": row.get("source_provider"),
                "source_service": row.get("source_service"),
                "resource_uid": None,
                "usage": usage,
                "confidence": 0.95,
                "warnings": [],
            }
        )
    return components


def _units(category: str, usage: dict[str, float]) -> dict[str, float]:
    quantity = usage.get("quantity", 1)
    hours = usage.get("hours", usage.get("active_hours", 0))
    units = {
        "vcpu_hour": usage.get("vcpu", 0) * hours * quantity,
        "memory_gb_hour": usage.get("memory_gb", 0) * hours * quantity,
        "storage_gb_month": usage.get("storage_gb", 0) * quantity,
        "backup_gb_month": usage.get("backup_gb", 0) * quantity,
        "egress_gb": usage.get("egress_gb", 0) * quantity,
        "requests_million": usage.get("requests_million", 0) * quantity,
        "processed_gb": usage.get("processed_gb", 0) * quantity,
        "operations_10k": usage.get("operations_10k", 0) * quantity,
        "lb_hour": usage.get("hours", 0) * quantity,
        "cluster_hour": usage.get("hours", 0) * quantity,
    }
    if category == "cache":
        units["memory_gb_hour"] = usage.get("memory_gb", 0) * usage.get("hours", 0) * quantity
    return units


def _discount(commitment_months: int) -> float:
    if commitment_months >= 36:
        return 0.72
    if commitment_months >= 12:
        return 0.88
    return 1.0


def _provider_estimate(
    provider: str,
    components: list[dict[str, Any]],
    commitment_months: int,
    rate_cards: dict[str, dict[str, dict[str, Any]]],
    apply_reference_discount: bool,
) -> dict[str, Any]:
    discount = _discount(commitment_months) if apply_reference_discount else 1.0
    services = []
    total_usd = 0.0
    for component in components:
        category = component["category"]
        card = rate_cards[provider][category]
        units = _units(category, component["usage"])
        lines = []
        subtotal = 0.0
        for metric, unit_price in card["rates"].items():
            consumed = units.get(metric, 0.0)
            amount = consumed * unit_price
            if consumed:
                lines.append(
                    {
                        "metric": metric,
                        "units": round(consumed, 4),
                        "unit_price_usd": unit_price,
                        "amount_usd": round(amount, 4),
                        "formula": f"{consumed:.4f} × {unit_price:.6f}",
                    }
                )
            subtotal += amount
        discounted = subtotal * discount
        total_usd += discounted
        services.append(
            {
                "component": component["name"],
                "category": category,
                "service": card["service"],
                "sku": card["sku"],
                "usage": component["usage"],
                "lines": lines,
                "subtotal_usd": round(subtotal, 2),
                "commitment_discount_pct": round((1 - discount) * 100, 1),
                "monthly_usd": round(discounted, 2),
            }
        )
    return {"provider": provider, "monthly_usd": round(total_usd, 2), "services": services}


def estimate(payload: dict[str, Any]) -> dict[str, Any]:
    scope_type = str(payload.get("scope_type") or "product")
    scope_value = payload.get("scope_value")
    targets = list(dict.fromkeys(payload.get("target_providers") or SUPPORTED_PROVIDERS))
    unsupported = [provider for provider in targets if provider not in SUPPORTED_PROVIDERS]
    if unsupported:
        raise ValueError(f"Unsupported target providers: {', '.join(unsupported)}")
    if not targets:
        raise ValueError("Select at least one target provider")

    if scope_type == "custom":
        components = _custom_components(payload.get("components") or [])
        resources: list[dict[str, Any]] = []
    else:
        resources = _select_resources(scope_type, str(scope_value) if scope_value is not None else None)
        components = [_resource_component(resource) for resource in resources]

    commitment_months = int(payload.get("commitment_months") or 0)
    if commitment_months not in {0, 12, 36}:
        raise ValueError("Commitment must be 0, 12 or 36 months")
    output_currency = str(payload.get("currency") or "BRL").upper()
    if output_currency not in {"USD", "BRL"}:
        raise ValueError("Currency must be USD or BRL")
    usd_to_brl = _number(payload.get("usd_to_brl"), 5.0)
    if usd_to_brl <= 0:
        raise ValueError("USD to BRL exchange rate must be positive")

    pricing_mode = str(payload.get("pricing_mode") or get_settings().migration_pricing_mode)
    if pricing_mode not in {"official", "official_preferred", "reference"}:
        raise ValueError("Pricing mode must be official, official_preferred or reference")
    if get_settings().environment.lower() == "production" and pricing_mode != "official":
        raise ValueError("Production estimates require official pricing")
    rate_cards = RATE_CARDS
    pricing_metadata: dict[str, Any] = {
        "kind": "reference",
        "catalog_version": CATALOG_VERSION,
        "fallback": False,
    }
    official_error = None
    if pricing_mode in {"official", "official_preferred"}:
        try:
            official = official_pricing_service.get_rates(
                targets, refresh_prices=bool(payload.get("refresh_prices"))
            )
            required_categories = {component["category"] for component in components}
            incomplete = {
                provider: sorted(required_categories - set((official["cards"].get(provider) or {}).keys()))
                for provider in targets
            }
            incomplete = {provider: rows for provider, rows in incomplete.items() if rows}
            if incomplete:
                raise official_pricing_service.PricingUnavailable(
                    "Official SKU mappings do not cover: "
                    + "; ".join(f"{provider}={','.join(rows)}" for provider, rows in incomplete.items())
                )
            rate_cards = official["cards"]
            pricing_metadata = {
                "kind": "official",
                "fetched_at": official["fetched_at"],
                "expires_at": official["expires_at"],
                "regions": official["regions"],
                "sources": official["sources"],
                "fallback": False,
            }
        except official_pricing_service.PricingUnavailable as exc:
            official_error = str(exc)
            if pricing_mode == "official":
                raise ValueError(official_error) from exc
            pricing_metadata["fallback"] = True
            pricing_metadata["official_error"] = official_error

    comparisons = []
    for provider in targets:
        comparison = _provider_estimate(
            provider,
            components,
            commitment_months,
            rate_cards,
            pricing_metadata["kind"] == "reference",
        )
        comparison["monthly_cost"] = round(
            comparison["monthly_usd"] * (usd_to_brl if output_currency == "BRL" else 1), 2
        )
        comparison["currency"] = output_currency
        comparisons.append(comparison)
    comparisons.sort(key=lambda item: item["monthly_cost"])

    observed = db.migration_observed_cost(scope_type, str(scope_value or ""), resources)
    observed_normalized = None
    if observed["amount"] and observed["currency"] in {"USD", "BRL"}:
        if observed["currency"] == output_currency:
            observed_normalized = observed["amount"]
        elif observed["currency"] == "BRL" and output_currency == "USD":
            observed_normalized = observed["amount"] / usd_to_brl
        elif observed["currency"] == "USD" and output_currency == "BRL":
            observed_normalized = observed["amount"] * usd_to_brl
    for comparison in comparisons:
        comparison["difference_vs_observed"] = (
            round(comparison["monthly_cost"] - observed_normalized, 2)
            if observed_normalized is not None
            else None
        )
        comparison["savings_pct_vs_observed"] = (
            round((observed_normalized - comparison["monthly_cost"]) / observed_normalized * 100, 1)
            if observed_normalized
            else None
        )

    warnings = sorted({warning for component in components for warning in component["warnings"]})
    if pricing_metadata["kind"] == "reference":
        warnings.append("Catálogo de referência: não inclui impostos, suporte, descontos privados, free tier nem preços spot.")
        if official_error:
            warnings.append(f"Preço oficial indisponível; fallback de desenvolvimento: {official_error}")
    elif commitment_months:
        warnings.append(
            "Compromisso não recebeu desconto presumido: configure SKUs oficiais de reserva/savings plan para refletir o contrato."
        )
    warnings.append("Valide arquitetura, tráfego, alta disponibilidade e contrato privado antes de aprovar a migração.")
    confidence = round(sum(component["confidence"] for component in components) / len(components), 2)
    return {
        "id": f"estimate_{uuid.uuid4().hex[:16]}",
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_version": CATALOG_VERSION,
        "catalog_kind": pricing_metadata["kind"],
        "pricing": pricing_metadata,
        "scope": {"type": scope_type, "value": scope_value},
        "currency": output_currency,
        "usd_to_brl": usd_to_brl,
        "commitment_months": commitment_months,
        "observed_current": {**observed, "normalized_amount": round(observed_normalized, 2) if observed_normalized is not None else None, "normalized_currency": output_currency},
        "components": components,
        "comparisons": comparisons,
        "cheapest_provider": comparisons[0]["provider"],
        "confidence": confidence,
        "warnings": warnings,
    }


def create_scenario(name: str, payload: dict[str, Any], subject: str) -> dict[str, Any]:
    result = estimate(payload)
    return db.create_migration_scenario(
        {
            "id": f"mig_{uuid.uuid4().hex[:16]}",
            "name": name,
            "scope_type": result["scope"]["type"],
            "scope_value": result["scope"].get("value"),
            "currency": result["currency"],
            "catalog_version": result["catalog_version"],
            "request": payload,
            "result": result,
            "created_by": subject,
        }
    )

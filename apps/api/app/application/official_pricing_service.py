from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

from app.core import db
from app.core.config import get_settings

CACHE_KEY = "migration_official_pricing_cache"
MAPPINGS_KEY = "migration_official_sku_mappings"
DEFAULT_REGIONS = {
    "aws": "sa-east-1",
    "gcp": "southamerica-east1",
    "azure": "brazilsouth",
    "oci": "sa-saopaulo-1",
}


class PricingUnavailable(RuntimeError):
    pass


def get_config() -> dict[str, Any]:
    saved_regions = db.get_setting("migration_pricing_regions") or {}
    return {
        "mode": get_settings().migration_pricing_mode,
        "cache_hours": get_settings().migration_pricing_cache_hours,
        "regions": {**DEFAULT_REGIONS, **saved_regions},
        "mappings": db.get_setting(MAPPINGS_KEY) or {},
        "gcp_catalog_configured": bool(get_settings().gcp_billing_catalog_api_key),
    }


def save_config(regions: dict[str, str], mappings: dict[str, Any]) -> dict[str, Any]:
    normalized_regions = {provider: str(regions.get(provider) or DEFAULT_REGIONS[provider]) for provider in DEFAULT_REGIONS}
    db.set_setting("migration_pricing_regions", normalized_regions)
    db.set_setting(MAPPINGS_KEY, mappings)
    db.set_setting(CACHE_KEY, {})
    return get_config()


def _money(value: Any) -> float:
    if isinstance(value, dict):
        return float(value.get("units") or 0) + float(value.get("nanos") or 0) / 1_000_000_000
    return float(value)


def _azure_rate(mapping: dict[str, Any], region: str) -> tuple[float, dict[str, Any]]:
    selectors = [f"armRegionName eq '{region}'", "priceType eq 'Consumption'"]
    for field in ("meterId", "skuId", "armSkuName", "serviceName", "meterName"):
        if mapping.get(field):
            selectors.append(f"{field} eq '{mapping[field]}'")
    url = "https://prices.azure.com/api/retail/prices?api-version=2023-01-01-preview&$filter=" + quote(" and ".join(selectors), safe="()'$=")
    with httpx.Client(timeout=30) as client:
        response = client.get(url)
        response.raise_for_status()
        items = response.json().get("Items") or []
    if not items:
        raise PricingUnavailable(f"Azure meter not found in {region}: {mapping}")
    item = min(items, key=lambda row: float(row.get("retailPrice") or 0) or float("inf"))
    return float(item["retailPrice"]) * float(mapping.get("multiplier", 1)), {
        "provider": "azure",
        "region": region,
        "sku": item.get("skuId") or item.get("armSkuName"),
        "meter": item.get("meterName"),
        "unit": item.get("unitOfMeasure"),
        "effective_at": item.get("effectiveStartDate"),
        "source_url": url,
    }


def _gcp_rate(mapping: dict[str, Any], region: str) -> tuple[float, dict[str, Any]]:
    api_key = get_settings().gcp_billing_catalog_api_key
    service_id = mapping.get("service_id")
    sku_id = mapping.get("sku_id")
    if not api_key:
        raise PricingUnavailable("GCP Billing Catalog API key is not configured")
    if not service_id or not sku_id:
        raise PricingUnavailable("GCP mapping requires service_id and sku_id")
    url = f"https://cloudbilling.googleapis.com/v1/services/{service_id}/skus?key={api_key}"
    token = ""
    selected = None
    with httpx.Client(timeout=30) as client:
        while True:
            response = client.get(url, params={"key": api_key, "pageSize": 5000, **({"pageToken": token} if token else {})})
            response.raise_for_status()
            payload = response.json()
            selected = next((row for row in payload.get("skus", []) if row.get("skuId") == sku_id), None)
            if selected or not payload.get("nextPageToken"):
                break
            token = payload["nextPageToken"]
    if not selected or (selected.get("serviceRegions") and region not in selected["serviceRegions"] and "global" not in selected["serviceRegions"]):
        raise PricingUnavailable(f"GCP SKU {sku_id} is unavailable in {region}")
    pricing = (selected.get("pricingInfo") or [None])[0] or {}
    expression = pricing.get("pricingExpression") or {}
    tiers = expression.get("tieredRates") or []
    if not tiers:
        raise PricingUnavailable(f"GCP SKU {sku_id} has no public tiered rate")
    price = _money(tiers[0].get("unitPrice") or {})
    return price * float(mapping.get("multiplier", 1)), {
        "provider": "gcp",
        "region": region,
        "sku": sku_id,
        "meter": selected.get("description"),
        "unit": expression.get("usageUnit"),
        "effective_at": pricing.get("effectiveTime"),
        "source_url": f"https://cloudbilling.googleapis.com/v1/services/{service_id}/skus",
    }


def _aws_rate(mapping: dict[str, Any], region: str) -> tuple[float, dict[str, Any]]:
    service_code = mapping.get("service_code")
    sku = mapping.get("sku")
    if not service_code or not sku:
        raise PricingUnavailable("AWS mapping requires service_code and sku")
    url = f"https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/{service_code}/current/{region}/index.csv"
    selected = None
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            reader = csv.DictReader(response.iter_lines())
            for row in reader:
                if row.get("SKU") != sku or row.get("TermType") != "OnDemand":
                    continue
                if mapping.get("unit") and row.get("Unit") != mapping["unit"]:
                    continue
                selected = row
                break
    if not selected:
        raise PricingUnavailable(f"AWS on-demand SKU {sku} not found in {region}")
    price = float(selected.get("PricePerUnit") or 0)
    return price * float(mapping.get("multiplier", 1)), {
        "provider": "aws",
        "region": region,
        "sku": sku,
        "meter": selected.get("RateCode") or selected.get("Description"),
        "unit": selected.get("Unit"),
        "effective_at": selected.get("EffectiveDate"),
        "source_url": url,
    }


def _oci_rate(mapping: dict[str, Any], region: str) -> tuple[float, dict[str, Any]]:
    part_number = mapping.get("part_number") or mapping.get("partNumber")
    if not part_number:
        raise PricingUnavailable("OCI mapping requires part_number")
    endpoint = "https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/"
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(endpoint, params={"partNumber": part_number, "currencyCode": "USD"})
        response.raise_for_status()
        items = response.json().get("items") or []
    item = next((row for row in items if row.get("partNumber") == part_number), None)
    if not item:
        raise PricingUnavailable(f"OCI part number {part_number} was not found")
    currency = next((row for row in item.get("prices") or [] if row.get("currencyCode") == "USD"), None)
    tiers = (currency or {}).get("prices") or []
    model = mapping.get("model", "PAY_AS_YOU_GO")
    matching_tiers = [row for row in tiers if row.get("model") == model]
    if mapping.get("range_min") is not None:
        matching_tiers = [row for row in matching_tiers if str(row.get("rangeMin")) == str(mapping["range_min"])]
    if not matching_tiers:
        raise PricingUnavailable(f"OCI part number {part_number} has no USD {model} price")
    tier = matching_tiers[0]
    price = float(tier.get("value") or 0)
    source_url = f"{endpoint}?partNumber={quote(str(part_number))}&currencyCode=USD"
    return price * float(mapping.get("multiplier", 1)), {
        "provider": "oci",
        "region": region,
        "sku": part_number,
        "meter": item.get("displayName"),
        "unit": item.get("metricName"),
        "effective_at": None,
        "source_url": source_url,
    }


FETCHERS = {"aws": _aws_rate, "gcp": _gcp_rate, "azure": _azure_rate, "oci": _oci_rate}


def refresh(providers: list[str] | None = None) -> dict[str, Any]:
    config = get_config()
    mappings = config["mappings"]
    requested = providers or list(FETCHERS)
    cards: dict[str, dict[str, Any]] = {}
    sources: list[dict[str, Any]] = []
    errors: dict[str, list[str]] = {}
    for provider in requested:
        provider_mappings = mappings.get(provider) or {}
        if not provider_mappings:
            errors.setdefault(provider, []).append("No official SKU mappings configured")
            continue
        for category, definition in provider_mappings.items():
            card = {"service": definition.get("service"), "sku": definition.get("sku"), "rates": {}}
            for metric, mapping in (definition.get("metrics") or {}).items():
                try:
                    rate, source = FETCHERS[provider](mapping, config["regions"][provider])
                    card["rates"][metric] = rate
                    sources.append({"category": category, "metric": metric, **source})
                except Exception as exc:  # noqa: BLE001
                    errors.setdefault(provider, []).append(f"{category}.{metric}: {str(exc)[:240]}")
            if card["rates"]:
                cards.setdefault(provider, {})[category] = card
    result = {
        "kind": "official",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=config["cache_hours"])).isoformat(),
        "regions": config["regions"],
        "cards": cards,
        "sources": sources,
        "errors": errors,
    }
    db.set_setting(CACHE_KEY, result)
    return result


def get_rates(providers: list[str], *, refresh_prices: bool = False) -> dict[str, Any]:
    cached = db.get_setting(CACHE_KEY) or {}
    expired = True
    if cached.get("expires_at"):
        expired = datetime.fromisoformat(cached["expires_at"]) <= datetime.now(timezone.utc)
    if refresh_prices or expired or any(provider not in (cached.get("cards") or {}) for provider in providers):
        cached = refresh(providers)
    missing = [provider for provider in providers if provider not in (cached.get("cards") or {})]
    if missing:
        details = "; ".join(f"{provider}: {', '.join((cached.get('errors') or {}).get(provider, []))}" for provider in missing)
        raise PricingUnavailable(f"Official pricing unavailable for {', '.join(missing)}. {details}")
    return cached

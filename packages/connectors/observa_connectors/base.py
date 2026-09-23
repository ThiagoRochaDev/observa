from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class CostSignal:
    """observa.cost.v1"""

    date: date
    provider: str
    amount: float
    currency: str = "BRL"
    account: str | None = None
    service: str | None = None
    resource_id: str | None = None
    product: str | None = None
    squad: str | None = None
    environment: str | None = None
    sku: str | None = None


@dataclass
class ResourceSignal:
    """observa.resource.v1"""

    provider: str
    type: str
    id: str
    name: str | None = None
    region: str | None = None
    product: str | None = None
    squad: str | None = None
    status: str | None = None
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSignal:
    """observa.metric.v1"""

    name: str
    value: float
    ts: datetime
    unit: str = ""
    resource_id: str | None = None
    product: str | None = None
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class LogSignal:
    """observa.log.v1"""

    ts: datetime
    severity: str
    source: str
    message: str
    product: str | None = None
    service: str | None = None
    trace_id: str | None = None
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class PullResult:
    costs: list[CostSignal] = field(default_factory=list)
    resources: list[ResourceSignal] = field(default_factory=list)
    metrics: list[MetricSignal] = field(default_factory=list)
    logs: list[LogSignal] = field(default_factory=list)
    message: str = ""


@dataclass
class TestResult:
    ok: bool
    message: str = ""


@dataclass
class ActionResult:
    ok: bool
    message: str = ""
    external_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    id: str
    name: str
    description: str = ""
    capabilities: list[str] = []
    #: category used to group the connector catalog in the UI —
    #: "cloud" | "observability" | "incident" | "vcs_cicd" | "on_prem" | "saas" | "demo"
    category: str = "saas"
    #: short slug the frontend maps to a badge color/monogram (see PROVIDER_META in lib/api.ts)
    icon: str = "generic"
    #: docs URL shown next to the credential form (where to generate a PAT/token)
    docs_url: str = ""

    @abstractmethod
    def config_schema(self) -> dict[str, Any]:
        """JSON Schema for UI form (non-secret fields)."""

    def secrets_schema(self) -> dict[str, Any]:
        """JSON Schema for secret fields (API keys, SA JSON, …)."""
        return {"type": "object", "properties": {}}

    @abstractmethod
    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        ...

    @abstractmethod
    def pull(
        self,
        config: dict[str, Any],
        secrets: dict[str, Any],
        *,
        since: date | None = None,
    ) -> PullResult:
        ...

    def apply_tags(
        self,
        config: dict[str, Any],
        secrets: dict[str, Any],
        *,
        resource: dict[str, Any],
        tags: dict[str, str],
        dry_run: bool = True,
    ) -> ActionResult:
        raise NotImplementedError(f"Connector {self.id} does not support tag write-back")

    def change_power_state(
        self,
        config: dict[str, Any],
        secrets: dict[str, Any],
        *,
        resource: dict[str, Any],
        action: str,
        dry_run: bool = True,
    ) -> ActionResult:
        raise NotImplementedError(f"Connector {self.id} does not support power actions")

    def apply_remediation(
        self,
        config: dict[str, Any],
        secrets: dict[str, Any],
        *,
        proposal: dict[str, Any],
        dry_run: bool = True,
    ) -> ActionResult:
        raise NotImplementedError(f"Connector {self.id} does not support remediation actions")

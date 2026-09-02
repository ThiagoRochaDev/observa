from __future__ import annotations

from typing import Any

from observa_connectors.base import BaseConnector, PullResult, TestResult


class _StubConnector(BaseConnector):
    """UI-ready stub — credential form + catalog entry work now; `pull()` ships next.

    Use this for connectors that are in the catalog (so clients can already
    see the tool, its icon, and fill in credentials) but whose real API
    integration hasn't been wired up yet. Swap `_StubConnector` for
    `BaseConnector` and implement `test_connection`/`pull` the same way the
    ones in `providers/` do, once you're ready (see `providers/bitbucket.py`,
    `providers/opsgenie.py`, etc. for connectors that started out exactly
    like this and later got a real implementation).
    """

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        return TestResult(
            ok=False,
            message="Connector stub: credential form works; data pull ships in a future release.",
        )

    def pull(self, config: dict[str, Any], secrets: dict[str, Any], *, since=None) -> PullResult:
        raise NotImplementedError(self.id)

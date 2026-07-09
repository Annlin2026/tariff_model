"""Linux-friendly DAX execution via Fabric REST `executeQueries` endpoint.

Alternative to pyadomd (Windows-only via ADOMD.NET) — works from any platform
using a plain HTTP POST with an SP bearer token.

Endpoint:
    POST https://api.powerbi.com/v1.0/myorg/groups/{groupId}/datasets/{datasetId}/executeQueries

Reference: https://learn.microsoft.com/rest/api/power-bi/datasets/execute-queries

Usage:
    from scripts.fabric_dax_client import FabricDAXClient
    cli = FabricDAXClient.from_env(environment="uat")
    rows = cli.query("EVALUATE TOPN(5, fact_market_import_situation)")
    # rows: list[dict[str, Any]] — each dict keyed by column display names

Constraints (per REST API docs):
    - One `EVALUATE` statement per call (use DEFINE + EVALUATE for measures)
    - 15 MB response body cap
    - 100k-row result cap
    - 10-call/min/user throttle
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests
from azure.identity import ClientSecretCredential

PBI_API_SCOPE = "https://analysis.windows.net/powerbi/api/.default"
PBI_API_BASE = "https://api.powerbi.com/v1.0/myorg"


class ExecuteQueriesNotAuthorized(RuntimeError):
    """Raised when Fabric executeQueries returns 401 PowerBINotAuthorizedException.

    Typically means the tenant flag "Dataset Execute Queries REST API" is
    disabled for service principals (separate from the general "SP can use
    Fabric APIs" flag). See docs/letters/2026-04-22-tenant-admin-executequeries-flag.md.
    """


@dataclass
class FabricDAXClient:
    workspace_id: str
    dataset_name: str
    _token: str
    _dataset_id: str | None = None

    @classmethod
    def from_env(
        cls,
        environment: str = "dev",
        dataset_name: str | None = None,
    ) -> FabricDAXClient:
        env_key = f"FABRIC_WORKSPACE_{environment.upper()}"
        workspace_id = os.environ[env_key]
        cred = ClientSecretCredential(
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"],
        )
        token = cred.get_token(PBI_API_SCOPE).token
        return cls(
            workspace_id=workspace_id,
            dataset_name=dataset_name or os.environ.get("SPIKE_MODEL_NAME", "itrade_trade_model"),
            _token=token,
        )

    def _hdr(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    @property
    def dataset_id(self) -> str:
        if self._dataset_id is None:
            r = requests.get(
                f"{PBI_API_BASE}/groups/{self.workspace_id}/datasets",
                headers=self._hdr(),
                timeout=30,
            )
            r.raise_for_status()
            matches = [d for d in r.json()["value"] if d["name"] == self.dataset_name]
            if len(matches) != 1:
                raise RuntimeError(
                    f"expected 1 dataset named {self.dataset_name!r} in workspace "
                    f"{self.workspace_id}; found {len(matches)}"
                )
            self._dataset_id = matches[0]["id"]
        return self._dataset_id

    def query(self, dax: str, *, include_nulls: bool = True) -> list[dict[str, Any]]:
        """Run a single EVALUATE statement; return rows as list[dict].

        Column keys in returned dicts use Power BI's display names exactly as
        the REST API returns them — typically `'tablename'[columnname]` or
        the measure name for measure outputs.
        """
        body = {
            "queries": [{"query": dax}],
            "serializerSettings": {"includeNulls": include_nulls},
        }
        r = requests.post(
            f"{PBI_API_BASE}/groups/{self.workspace_id}/datasets/{self.dataset_id}/executeQueries",
            headers=self._hdr(),
            json=body,
            timeout=120,
        )
        if r.status_code == 401 and "PowerBINotAuthorizedException" in r.text:
            raise ExecuteQueriesNotAuthorized(
                "executeQueries 401 — tenant flag 'Dataset Execute Queries REST API' "
                "likely disabled for SPs (separate from the general SP-Fabric-APIs flag). "
                f"Raw: {r.text[:300]}"
            )
        if r.status_code >= 400:
            raise RuntimeError(
                f"executeQueries {r.status_code}: {r.text[:500]}"
            )
        payload = r.json()
        results = payload.get("results", [])
        if not results:
            return []
        first = results[0]
        if "error" in first:
            raise RuntimeError(f"DAX error: {first['error']}")
        tables = first.get("tables", [])
        if not tables:
            return []
        return tables[0].get("rows", [])

    def query_scalar(self, dax: str) -> Any:
        """Run a single-row single-column scalar query; return the value."""
        rows = self.query(dax)
        if not rows:
            return None
        first_row = rows[0]
        if not first_row:
            return None
        return next(iter(first_row.values()))

"""Shared pytest fixtures for iTrade PBI tests."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def sp_credential():
    """Azure ClientSecretCredential — skips if SP env vars missing."""
    missing = [v for v in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")
               if not os.environ.get(v)]
    if missing:
        pytest.skip(f"SP env vars missing: {missing}")
    from azure.identity import ClientSecretCredential
    return ClientSecretCredential(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        client_id=os.environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
    )


@pytest.fixture(scope="session")
def powerbi_token(sp_credential) -> str:
    return sp_credential.get_token(
        "https://analysis.windows.net/powerbi/api/.default"
    ).token


@pytest.fixture(scope="session")
def workspace_id() -> str:
    ws = os.environ.get("FABRIC_WORKSPACE_DEV")
    if not ws:
        pytest.skip("FABRIC_WORKSPACE_DEV not set")
    return ws


@pytest.fixture(scope="session")
def xmla_conn_str(powerbi_token: str, workspace_id: str) -> str:
    """Build a Pyadomd connection string from the SP bearer token."""
    dataset = os.environ.get("SPIKE_MODEL_NAME", "itrade_trade_model")
    return (
        f"Provider=MSOLAP;"
        f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/{workspace_id};"
        f"Initial Catalog={dataset};"
        f"Password={powerbi_token}"
    )


@pytest.fixture(scope="session")
def xmla_client(xmla_conn_str: str):
    """Yield a pyadomd connection (Windows only)."""
    if sys.platform != "win32":
        pytest.skip("pyadomd requires Windows")
    try:
        from pyadomd import Pyadomd  # type: ignore[import-not-found]
    except ImportError:
        pytest.skip("pyadomd not installed")
    with Pyadomd(xmla_conn_str) as conn:
        yield conn


@pytest.fixture(scope="session")
def dax_client(sp_credential):
    """Cross-platform DAX client via Fabric REST executeQueries.

    Replaces pyadomd on Linux/macOS. Defaults to DEV workspace; override via
    `FABRIC_TEST_ENVIRONMENT=uat` env var for live UAT verification.
    """
    if not os.environ.get("FABRIC_WORKSPACE_DEV"):
        pytest.skip("FABRIC_WORKSPACE_DEV not set")
    from scripts.fabric_dax_client import FabricDAXClient

    env = os.environ.get("FABRIC_TEST_ENVIRONMENT", "dev")
    return FabricDAXClient.from_env(environment=env)


@pytest.fixture(scope="session")
def golden_mapping() -> dict[str, Any]:
    """Load Chinese CSV header → (table, column|measure) mapping.

    P0 skips tests using this fixture since the mapping file is created in P2a
    when first golden CSV is wired up.
    """
    mapping_path = REPO_ROOT / "semantic_model" / "translations" / "zh-TW.json"
    if not mapping_path.exists():
        pytest.skip(
            f"golden mapping not yet wired ({mapping_path} absent) — P2a creates it"
        )
    with mapping_path.open("r", encoding="utf-8") as f:
        return json.load(f)

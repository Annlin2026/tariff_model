"""Per-directory fixtures for the tariff test suite."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_LIVE_ENV_VARS = (
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "FABRIC_WORKSPACE_DEV",
)


def requires_live_env() -> None:
    """Skip the test unless on Windows with SP creds + workspace env.

    Used by tariff live-gated tests (Iter 6-13). Call it at the top of each
    test body — it raises pytest.skip() and exits cleanly on dev Linux hosts.
    """
    missing = [v for v in REQUIRED_LIVE_ENV_VARS if not os.environ.get(v)]
    if missing:
        pytest.skip(f"live creds missing: {missing}")
    if sys.platform != "win32":
        pytest.skip("pyadomd requires Windows")


@pytest.fixture(scope="session")
def deploy_evidence_path() -> Path:
    return REPO_ROOT / "status" / "tariff_deploy_evidence.json"


@pytest.fixture
def dax_query(xmla_client):
    """Return a callable `dax(query_str) -> list[dict]`.

    Requires the session-scoped `xmla_client` fixture from tests/conftest.py,
    which itself skips unless on Windows with pyadomd + SP creds.
    """
    def _run(query: str) -> list[dict]:
        with xmla_client.cursor() as cur:
            cur.execute(query)
            cols = [c.name for c in cur.description]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
    return _run

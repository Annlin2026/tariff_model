"""Post-deploy smoke for the tariff slice.

Runs only on Windows with SP creds and FABRIC_WORKSPACE_DEV set. On a
dev-Linux host every test in here pytest.skips cleanly.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from tests.tariff.conftest import requires_live_env

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_deploy_and_frame_returns_timing(deploy_evidence_path):
    requires_live_env()
    from scripts.deploy_model import deploy_and_frame

    result = deploy_and_frame(
        workspace_id=os.environ["FABRIC_WORKSPACE_DEV"],
        dataset_name=os.environ.get("SPIKE_MODEL_NAME", "itrade_trade_model"),
        environment="dev",
        repository_directory=REPO_ROOT,
        deploy_reports_after=False,
    )
    assert result["framing_seconds"] > 0
    deploy_evidence_path.parent.mkdir(parents=True, exist_ok=True)
    deploy_evidence_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def test_avg_tariff_rate_measure_non_null(dax_query):
    requires_live_env()
    rows = dax_query(
        "EVALUATE ROW(\"v\", CALCULATE([Avg Tariff Rate %]))"
    )
    assert len(rows) == 1
    v = rows[0].get("[v]")
    assert v is not None, "Avg Tariff Rate % came back NULL — deploy or data issue"

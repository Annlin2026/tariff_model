"""Deploy the split tariff model to the target workspace as the az-login user.

The spec's `scripts/deploy_model.py::deploy_and_frame` builds its credential
from SP env vars (ClientSecretCredential). The KV service principal
(taitra-mcp-fabric) has no role on the target workspace IH_DataTeam_Ann
(aa4e76f5-…) yet, so this runner re-composes the exact same
deploy → resolve dataset → TakeOver → refresh → wait_for_framing sequence
using `AzureCliCredential` and the spec's own functions, unmodified.

Once the workspace admin adds the SP as Member, switch back to:
    python -m scripts.deploy_model --workspace-id $FABRIC_WORKSPACE_DEV \
        --environment dev --dataset-name itrade_tariff_model
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

from scripts.deploy_model import deploy_semantic_model
from scripts.wait_for_framing import (
    acquire_powerbi_token,
    trigger_refresh,
    wait_for_framing,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_NAME = "itrade_tariff_model"


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    workspace_id = os.environ["FABRIC_WORKSPACE_DEV"]
    cred = AzureCliCredential()

    # 1. Deploy model (spec function, user credential)
    deploy_semantic_model(workspace_id, "dev", REPO_ROOT / "semantic_model", cred)

    # 2. Resolve dataset_id via Power BI REST (mirrors deploy_and_frame step 2)
    pbi_token = acquire_powerbi_token(cred)
    resp = requests.get(
        f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets",
        headers={"Authorization": f"Bearer {pbi_token}"},
        timeout=60,
    )
    resp.raise_for_status()
    matches = [d for d in resp.json().get("value", []) if d.get("name") == DATASET_NAME]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly 1 dataset named {DATASET_NAME!r}; found {len(matches)}"
        )
    dataset_id = matches[0]["id"]

    # 2.5 TakeOver (mirrors deploy_and_frame step 2.5)
    takeover = requests.post(
        f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
        f"/datasets/{dataset_id}/Default.TakeOver",
        headers={"Authorization": f"Bearer {pbi_token}"},
        timeout=60,
    )
    if takeover.status_code not in (200, 202):
        print(
            f"TakeOver returned {takeover.status_code} {takeover.text[:200]}; continuing.",
            file=sys.stderr,
        )

    # 3. Trigger refresh + wait_for_framing (spec functions)
    request_id = trigger_refresh(workspace_id, dataset_id, pbi_token)
    framing_s = wait_for_framing(workspace_id, dataset_id, request_id, pbi_token, timeout=300)

    result = {
        "dataset_name": DATASET_NAME,
        "dataset_id": dataset_id,
        "workspace_id": workspace_id,
        "request_id": request_id,
        "framing_seconds": round(framing_s, 2),
        "credential": "AzureCliCredential (user; SP lacks workspace role)",
    }
    evidence = REPO_ROOT / "status" / "tariff_deploy_evidence.json"
    evidence.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

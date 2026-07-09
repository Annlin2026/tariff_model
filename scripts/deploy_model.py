"""Deploy TMDL semantic model to Fabric workspace via fabric-cicd.

Research anchors:
- fabric-cicd 0.1.34: FabricWorkspace(workspace_id, repository_directory,
  item_type_in_scope, environment, token_credential); publish_all_items(ws)
- Deploy SemanticModel and Report SEPARATELY (two FabricWorkspace instances),
  model first because report binds to model.

Usage:
  python scripts/deploy_model.py \
      --workspace-id $FABRIC_WORKSPACE_DEV \
      --environment dev \
      --repository-directory .
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Final

import requests
from azure.identity import ClientSecretCredential
from fabric_cicd import FabricWorkspace, publish_all_items

from scripts.wait_for_framing import (
    acquire_powerbi_token,
    trigger_refresh,
    wait_for_framing,
)

REPO_ROOT: Final = Path(__file__).resolve().parent.parent


def _credential() -> ClientSecretCredential:
    return ClientSecretCredential(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        client_id=os.environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
    )


def deploy_semantic_model(
    workspace_id: str,
    environment: str,
    repository_directory: Path,
    credential: ClientSecretCredential | None = None,
) -> None:
    """Publish the SemanticModel folder only (not reports)."""
    cred = credential or _credential()
    ws = FabricWorkspace(
        workspace_id=workspace_id,
        repository_directory=str(repository_directory),
        item_type_in_scope=["SemanticModel"],
        environment=environment,
        token_credential=cred,
    )
    publish_all_items(ws)


def deploy_reports(
    workspace_id: str,
    environment: str,
    repository_directory: Path,
    credential: ClientSecretCredential | None = None,
) -> None:
    """Publish Report folder(s) only. Call AFTER deploy_semantic_model."""
    cred = credential or _credential()
    ws = FabricWorkspace(
        workspace_id=workspace_id,
        repository_directory=str(repository_directory),
        item_type_in_scope=["Report"],
        environment=environment,
        token_credential=cred,
    )
    publish_all_items(ws)


def deploy_and_frame(
    workspace_id: str,
    dataset_name: str,
    environment: str,
    repository_directory: Path,
    deploy_reports_after: bool = False,
    framing_timeout: int = 300,
) -> dict[str, float | str]:
    """Deploy model, wait for framing, optionally deploy reports. Returns timing dict."""
    cred = _credential()

    # 1. Deploy model
    deploy_semantic_model(workspace_id, environment, repository_directory, cred)

    # 2. Resolve dataset_id via Power BI REST (fabric-cicd doesn't return it)
    # pbi_token is valid ~1h; current flow (deploy→framing ≤300s) stays well
    # within that. Do NOT reuse `pbi_token` after long operations — call
    # acquire_powerbi_token(cred) again. `cred` itself refreshes transparently.
    pbi_token = acquire_powerbi_token(cred)
    resp = requests.get(
        f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets",
        headers={"Authorization": f"Bearer {pbi_token}"},
        timeout=60,
    )
    resp.raise_for_status()
    datasets = resp.json().get("value", [])
    matches = [d for d in datasets if d.get("name") == dataset_name]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly 1 dataset named {dataset_name!r} in workspace "
            f"{workspace_id}; found {len(matches)}. All datasets: "
            f"{[d.get('name') for d in datasets]}"
        )
    dataset_id = matches[0]["id"]

    # 2.5 TakeOver: ensure the deploying SP owns the dataset so scheduled
    # refreshes + executeQueries always run as SP (not an interactive user
    # who may be off-shift / token expired). Safe to call repeatedly —
    # 200 on success, no-op if SP already owner. ADR 0018 §2.2 carry-fwd.
    takeover_resp = requests.post(
        f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/Default.TakeOver",
        headers={"Authorization": f"Bearer {pbi_token}"},
        timeout=60,
    )
    if takeover_resp.status_code not in (200, 202):
        print(
            f"deploy_and_frame: TakeOver returned {takeover_resp.status_code} "
            f"{takeover_resp.text[:200]}; continuing (framing may still work but "
            "scheduled refresh ownership unchanged).",
            file=sys.stderr,
        )

    # 3. Trigger refresh + wait_for_framing
    request_id = trigger_refresh(workspace_id, dataset_id, pbi_token)
    framing_s = wait_for_framing(
        workspace_id, dataset_id, request_id, pbi_token, timeout=framing_timeout
    )

    # 4. Deploy reports (optional; skipped at P0/P1 where no .Report folders exist yet)
    if deploy_reports_after:
        report_folders = list(repository_directory.rglob("*.Report"))
        if not report_folders:
            print(
                f"deploy_and_frame: deploy_reports_after=True but no *.Report "
                f"folders found under {repository_directory}; skipping reports deploy.",
                file=sys.stderr,
            )
        else:
            deploy_reports(workspace_id, environment, repository_directory, cred)

    return {
        "dataset_id": dataset_id,
        "request_id": request_id,
        "framing_seconds": round(framing_s, 2),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace-id", required=True)
    p.add_argument("--environment", required=True, choices=["dev", "uat", "prod"])
    # Default to semantic_model/ subdir. reports/_design_reference_pbip/
    # contains 5 design-reference .pbip bundles (bike / plastics PROD
    # designs) with nested *.SemanticModel + *.Report folders. Those are
    # design inspiration only — NOT to be published to the workspace.
    # Scanning from REPO_ROOT would make fabric-cicd pick them up as
    # deployable items. Override --repository-directory only when reports/
    # holds real, intended-to-publish content.
    p.add_argument(
        "--repository-directory",
        default=str(REPO_ROOT / "semantic_model"),
    )
    p.add_argument("--dataset-name", default="itrade_trade_model")
    p.add_argument(
        "--with-reports",
        action="store_true",
        help="Also deploy *.Report folders after framing. Off by default; "
             "no-op if no .Report folders exist in the repo.",
    )
    p.add_argument("--framing-timeout", type=int, default=300)
    args = p.parse_args()

    result = deploy_and_frame(
        workspace_id=args.workspace_id,
        dataset_name=args.dataset_name,
        environment=args.environment,
        repository_directory=Path(args.repository_directory),
        deploy_reports_after=args.with_reports,
        framing_timeout=args.framing_timeout,
    )
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()

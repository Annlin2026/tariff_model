"""Direct Lake framing wait via Power BI REST API.

Research anchor: research Agent confirmed REST API
  POST /groups/{workspaceId}/datasets/{datasetId}/refreshes → requestId
  GET  /groups/{workspaceId}/datasets/{datasetId}/refreshes/{requestId} → status

DO NOT use `time.sleep()` as a substitute for polling. The Ralph Loop boot
prompt (PROMPT.md hard rule 9) forbids it.
"""

from __future__ import annotations

import os
import time
from typing import Final

import requests
from azure.identity import ClientSecretCredential

POWERBI_RESOURCE: Final = "https://analysis.windows.net/powerbi/api/.default"
BASE_URL: Final = "https://api.powerbi.com/v1.0/myorg/groups"


class FramingTimeoutError(TimeoutError):
    """Raised when framing doesn't complete within the timeout."""


def _refresh_url(workspace_id: str, dataset_id: str, request_id: str | None = None) -> str:
    url = f"{BASE_URL}/{workspace_id}/datasets/{dataset_id}/refreshes"
    if request_id:
        url += f"/{request_id}"
    return url


def acquire_powerbi_token(
    credential: ClientSecretCredential | None = None,
) -> str:
    """Return a Power BI bearer token from SP env vars (or provided credential)."""
    if credential is None:
        credential = ClientSecretCredential(
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"],
        )
    return credential.get_token(POWERBI_RESOURCE).token


def trigger_refresh(
    workspace_id: str,
    dataset_id: str,
    token: str,
    refresh_type: str = "full",
) -> str:
    """POST a refresh; return the requestId from headers."""
    resp = requests.post(
        _refresh_url(workspace_id, dataset_id),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"type": refresh_type, "notifyOption": "NoNotification"},
        timeout=60,
    )
    resp.raise_for_status()
    request_id = resp.headers.get("x-ms-request-id") or resp.headers.get("RequestId")
    if not request_id:
        raise RuntimeError(f"No request id in refresh response: {resp.headers}")
    return request_id


def wait_for_framing(
    workspace_id: str,
    dataset_id: str,
    request_id: str,
    token: str,
    timeout: int = 300,
    poll_interval: int = 10,
) -> float:
    """Poll GET /refreshes/{request_id} until status == Completed.

    Returns elapsed seconds. Raises FramingTimeoutError on timeout or
    RuntimeError on Failed status.
    """
    start = time.monotonic()
    url = _refresh_url(workspace_id, dataset_id, request_id)
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        status: str | None = None
        body: dict = {}
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
            body = resp.json()
            status = body.get("status")
        except requests.HTTPError as e:
            # 4xx → fatal (auth, bad id); 5xx → transient, keep polling
            sc = e.response.status_code if e.response is not None else None
            if sc is not None and 400 <= sc < 500:
                raise
            status = f"transient:HTTP{sc}"
        except (requests.ConnectionError, requests.Timeout) as e:
            status = f"transient:{type(e).__name__}"

        if status == "Completed":
            return time.monotonic() - start
        if status == "Failed":
            raise RuntimeError(
                f"Refresh Failed: {body.get('serviceExceptionJson')}"
            )
        if time.monotonic() - start > timeout:
            raise FramingTimeoutError(
                f"Framing not Completed within {timeout}s (last status={status})"
            )
        time.sleep(poll_interval)


def main() -> None:
    """CLI: wait_for_framing.py --workspace <id> --dataset <id>"""
    import argparse
    import json
    import sys

    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--poll-interval", type=int, default=10)
    args = p.parse_args()

    token = acquire_powerbi_token()
    request_id = trigger_refresh(args.workspace, args.dataset, token)
    elapsed = wait_for_framing(
        args.workspace, args.dataset, request_id, token,
        timeout=args.timeout, poll_interval=args.poll_interval,
    )
    print(json.dumps({"request_id": request_id, "elapsed_s": round(elapsed, 2)}))
    sys.exit(0)


if __name__ == "__main__":
    main()

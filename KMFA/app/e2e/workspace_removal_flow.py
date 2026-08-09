#!/usr/bin/env python3
"""Verify that the Owner-deleted ``/workspace`` page cannot reappear.

The check runs against the same HTTP service used by the browser E2E suite.
It covers the former direct path, trailing-slash form, descendant form, and
HEAD request so a fallback route or compatibility redirect cannot silently
restore the page.  The artifact contains paths and status codes only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


REMOVED_PATHS = ("/workspace", "/workspace/", "/workspace/anything")


def _request(base_url: str, path: str, method: str = "GET") -> tuple[int, dict[str, str], str]:
    request = Request(f"{base_url.rstrip('/')}{path}", method=method)
    try:
        with urlopen(request, timeout=20) as response:
            return (
                response.status,
                {key.lower(): value for key, value in response.headers.items()},
                response.read().decode("utf-8", errors="replace"),
            )
    except HTTPError as error:
        return (
            error.code,
            {key.lower(): value for key, value in error.headers.items()},
            error.read().decode("utf-8", errors="replace"),
        )


def _assert_removed(base_url: str, path: str, method: str = "GET") -> dict[str, object]:
    status, headers, body = _request(base_url, path, method)
    assert status == 404, f"{method} {path} restored the deleted page: {status}"
    assert headers.get("x-kmfa-shell-mode") != "public-workspace"
    assert "KMFA｜公开工作区" not in body
    return {"method": method, "path": path, "status": status}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    root_status, _, root_body = _request(args.base_url, "/")
    assert root_status == 200, f"root cockpit unavailable: {root_status}"
    assert "KMFA｜经营驾驶舱" in root_body
    assert "KMFA｜公开工作区" not in root_body

    results = [_assert_removed(args.base_url, path) for path in REMOVED_PATHS]
    results.append(_assert_removed(args.base_url, "/workspace", "HEAD"))
    report = {"root_status": root_status, "workspace_paths": results, "status": "PASS"}
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

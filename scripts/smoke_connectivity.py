"""Simple end-to-end check for backend connectivity."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test API connectivity and job flow")
    parser.add_argument("--base", default="http://localhost:8001")
    parser.add_argument("--company", default="Blue Star Ltd")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    s = requests.Session()

    r = s.get(f"{base}/api/v1/health", timeout=10)
    r.raise_for_status()
    print("health:", r.json())

    run = s.post(
        f"{base}/api/v1/pipeline/run",
        json={"company": args.company, "debug_financials": False},
        timeout=20,
    )
    run.raise_for_status()
    payload = run.json()
    job_id = payload.get("job_id")
    if not job_id:
        raise RuntimeError(f"No job_id returned: {payload}")

    print("job_id:", job_id)
    deadline = time.time() + 900
    while time.time() < deadline:
        st = s.get(f"{base}/api/v1/jobs/{job_id}/status", timeout=10)
        st.raise_for_status()
        data = st.json()
        print("status:", data.get("status"), "progress:", data.get("progress"))
        if data.get("status") == "completed":
            break
        if data.get("status") == "failed":
            raise RuntimeError(json.dumps(data, indent=2))
        time.sleep(3)

    res = s.get(f"{base}/api/v1/jobs/{job_id}/result", timeout=10)
    res.raise_for_status()
    print("result:", json.dumps(res.json(), indent=2)[:1000])

    dash = s.get(f"{base}/api/v1/dashboard/{args.company}", timeout=10)
    dash.raise_for_status()
    print("dashboard success")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

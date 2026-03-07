"""Run FastAPI backend for intelli-credit-engine."""

from __future__ import annotations

import argparse

import uvicorn


def main() -> int:
    """CLI entrypoint for FastAPI server startup."""
    parser = argparse.ArgumentParser(description="Run Intelli Credit Engine API")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload in local dev")
    args = parser.parse_args()
    uvicorn.run("src.api.server:app", host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

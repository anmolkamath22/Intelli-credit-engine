"""Interactive CAM explainer CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.assistant.cam_explainer_agent import CAMExplainerAgent
from src.utils.text_processing import slugify


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask CAM explainer questions")
    parser.add_argument("--company", required=True, help="Company name")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    proc_dir = root / "data" / "processed" / slugify(args.company)
    if not proc_dir.exists():
        print(json.dumps({"error": f"Processed folder not found: {proc_dir}"}, indent=2))
        return 1

    agent = CAMExplainerAgent(proc_dir)
    print("CAM Explainer ready. Type 'exit' to quit.")

    while True:
        try:
            q = input("\nQuestion> ").strip()
        except EOFError:
            break
        if not q or q.lower() in {"exit", "quit"}:
            break
        ans = agent.answer(q)
        print(json.dumps(ans, indent=2, ensure_ascii=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

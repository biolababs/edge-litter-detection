from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "LICENSE",
    "LICENSE-NOTICE.md",
    "MODEL_CARD.md",
    "SECURITY.md",
    "CITATION.cff",
    "CONTRIBUTING.md",
    "Dockerfile",
    "compose.yaml",
    "config/classes.yaml",
    "config/project.yaml",
    "config/data.example.yaml",
    "data/count-ground-truth.example.json",
    "docs/EXPERIMENT_PLAN.md",
    "docs/COUNTING.md",
    "docs/DEPLOYMENT.md",
    "docs/EVENT_SCHEMA.md",
    "docs/GITHUB_RELEASE.md",
    "docs/JETSON_INVENTORY_2026-10-20.md",
    "docs/MODEL_DECISION.md",
    "src/litter_edge/schema.py",
    "src/litter_edge/tracking.py",
    "src/litter_edge/runtime.py",
    "src/litter_edge/evaluate.py",
    "src/litter_edge/evaluate_counts.py",
    "schemas/detection-event.schema.json",
    "schemas/count-ground-truth.schema.json",
    "thesis/manuscript.md",
]

SECRET_PATTERNS = [
    re.compile(r"Roboflow[ \t]*\([ \t]*api_key[ \t]*=[ \t]*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"ROBOFLOW_API_KEY[ \t]*=[ \t]*[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?i)(password|secret|token)[ \t]*[:=][ \t]*['\"][^'\"]{8,}['\"]"),
]


def main() -> None:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if any(part in {"data", "models", "runs", "generated"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret in {path.relative_to(ROOT)}")

    manuscript = (ROOT / "thesis/manuscript.md").read_text(encoding="utf-8")
    if "Results: Pending Data and Testing" not in manuscript:
        errors.append("manuscript must retain an explicit pending-results section")
    if "30 frames per second" in manuscript:
        errors.append("unsupported legacy 30 FPS claim found")

    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        raise SystemExit(1)
    print("Release scaffold validation passed.")


if __name__ == "__main__":
    main()


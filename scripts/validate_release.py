from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "startup.sh",
    "tests/test_startup.sh",
    "prepare_test_data.py",
    "tests/test_demo_data.py",
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
    "config/separation.yaml",
    "config/model-release.json",
    "config/data.example.yaml",
    "data/count-ground-truth.example.json",
    "media/README.md",
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
    "src/litter_edge/sorting.py",
    "src/litter_edge/storage.py",
    "src/litter_edge/query.py",
    "src/litter_edge/discover.py",
    "src/litter_edge/model_fetch.py",
    "src/litter_edge/demo_data.py",
    "src/litter_edge/evaluate.py",
    "src/litter_edge/evaluate_counts.py",
    "schemas/detection-event.schema.json",
    "schemas/count-ground-truth.schema.json",
    "schemas/integration-event.schema.json",
    "docs/INPUT_SOURCES.md",
    "docs/SOFTWARE_AND_RESEARCH.md",
    "docs/TRUCK_INTEGRATION.md",
    "docs/INTEGRATION_EVENTS.md",
    "deploy/systemd/litter-edge-truck.service.example",
    "query_counts.py",
    "state/README.md",
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
    if not os.access(ROOT / "startup.sh", os.X_OK):
        errors.append("startup.sh must be executable")

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if any(
            part in {"data", "models", "runs", "generated", "state"}
            for part in path.parts
        ):
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

    local_link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    markdown_files = [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
    for markdown in markdown_files:
        text = markdown.read_text(encoding="utf-8")
        for target in local_link_pattern.findall(text):
            if (
                "://" in target
                or target.startswith("#")
                or target.startswith("mailto:")
            ):
                continue
            clean_target = unquote(target.split("#", 1)[0]).strip("<>")
            if clean_target and not (markdown.parent / clean_target).resolve().exists():
                errors.append(
                    "broken local Markdown link: "
                    f"{markdown.relative_to(ROOT)} -> {target}"
                )

    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_version_match = re.search(
        r'^version\s*=\s*"([^"]+)"',
        pyproject_text,
        re.MULTILINE,
    )
    project_version = (
        project_version_match.group(1) if project_version_match else "missing"
    )
    package_version = str(
        json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
    )
    citation_version = str(
        yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))[
            "version"
        ]
    )
    init_text = (ROOT / "src/litter_edge/__init__.py").read_text(encoding="utf-8")
    init_match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    observed_versions = {
        "pyproject.toml": project_version,
        "package.json": package_version,
        "CITATION.cff": citation_version,
        "src/litter_edge/__init__.py": (
            init_match.group(1) if init_match else "missing"
        ),
    }
    for source, version in observed_versions.items():
        if version != project_version:
            errors.append(
                f"version mismatch: {source} has {version}, expected {project_version}"
            )
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {project_version} " not in changelog:
        errors.append(f"CHANGELOG.md has no entry for version {project_version}")

    model_release = json.loads(
        (ROOT / "config/model-release.json").read_text(encoding="utf-8")
    )
    if model_release.get("schema_version") != "1.0":
        errors.append("config/model-release.json schema_version must be 1.0")
    release_status = model_release.get("status")
    release_url = model_release.get("url")
    release_sha256 = model_release.get("sha256")
    if release_status not in {"pending", "published"}:
        errors.append("config/model-release.json status must be pending or published")
    if release_status == "published":
        if not isinstance(release_url, str) or not release_url.startswith("https://"):
            errors.append("published model release requires an HTTPS URL")
        if not isinstance(release_sha256, str) or not re.fullmatch(
            r"[0-9a-fA-F]{64}", release_sha256
        ):
            errors.append("published model release requires a SHA-256 digest")
    elif release_url is not None or release_sha256 is not None:
        errors.append("pending model release must not define url or sha256")

    class_config = yaml.safe_load(
        (ROOT / "config/classes.yaml").read_text(encoding="utf-8")
    )
    project_config = yaml.safe_load(
        (ROOT / "config/project.yaml").read_text(encoding="utf-8")
    )
    separation_config = yaml.safe_load(
        (ROOT / "config/separation.yaml").read_text(encoding="utf-8")
    )
    class_names = {str(value) for value in class_config["names"].values()}
    separation_names = {
        str(value) for value in separation_config["destinations"].keys()
    }
    if class_names != separation_names:
        errors.append("separation destinations must match configured class names")
    if project_config.get("backend") != "grounding_dino":
        errors.append("the default backend must remain the public grounding_dino profile")
    if project_config.get("model") != "IDEA-Research/grounding-dino-tiny":
        errors.append("the default public model ID changed without release review")
    prompts = class_config.get("prompts")
    names = class_config.get("names")
    if not isinstance(prompts, dict) or set(prompts) != set(names):
        errors.append("open-vocabulary prompt IDs must match class IDs")
    if len(class_names) < 10:
        errors.append("the reusable default catalog must not regress to a narrow pilot")
    gitkeep_files = list(ROOT.rglob(".gitkeep"))
    if gitkeep_files:
        errors.append(
            "unnecessary .gitkeep placeholders found: "
            + ", ".join(str(path.relative_to(ROOT)) for path in gitkeep_files)
        )

    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        raise SystemExit(1)
    print("Release scaffold validation passed.")


if __name__ == "__main__":
    main()


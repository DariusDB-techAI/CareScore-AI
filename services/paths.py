from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_project_path(raw_path: str, *, base_dir: Path | None = None) -> Path:
    normalized = str(raw_path or "").strip()
    if not normalized:
        return (base_dir or PROJECT_ROOT)

    path = Path(normalized)
    if path.is_absolute():
        return path

    return (base_dir or PROJECT_ROOT) / path

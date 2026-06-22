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


def to_project_relative_path(path: Path | str) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except Exception:
        return candidate.as_posix()

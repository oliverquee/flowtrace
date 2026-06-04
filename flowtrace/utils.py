"""Shared helpers for FlowTrace."""

from __future__ import annotations

from pathlib import Path


EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "env",
    "flowtrace_output",
    "site-packages",
    "venv",
}


class FlowTraceError(Exception):
    """Raised when FlowTrace cannot complete an analysis run."""


def resolve_entry_path(entry: str | Path) -> Path:
    entry_path = Path(entry).resolve()
    if not entry_path.exists():
        raise FlowTraceError(f"Entry file does not exist: {entry_path}")
    if not entry_path.is_file():
        raise FlowTraceError(f"Entry path is not a file: {entry_path}")
    if entry_path.suffix != ".py":
        raise FlowTraceError(f"Entry file must be a Python file: {entry_path}")
    return entry_path


def resolve_project_root(entry_path: Path, project_root: str | Path | None) -> Path:
    root = Path(project_root).resolve() if project_root else entry_path.parent.resolve()
    if not root.exists():
        raise FlowTraceError(f"Project root does not exist: {root}")
    if not root.is_dir():
        raise FlowTraceError(f"Project root is not a directory: {root}")
    if not is_relative_to(entry_path, root):
        raise FlowTraceError(f"Entry file must be inside project root: {entry_path}")
    return root


def resolve_output_dir(output: str | Path) -> Path:
    return Path(output).resolve()


def iter_python_files(project_root: Path, exclude_flowtrace_source: bool = False) -> list[Path]:
    files: list[Path] = []
    own_source_root = flowtrace_source_root()
    for path in project_root.rglob("*.py"):
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if exclude_flowtrace_source and is_relative_to(path, own_source_root):
            continue
        files.append(path.resolve())
    return sorted(files)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def module_name_for_file(path: Path, root: Path) -> str:
    relative = path.resolve().relative_to(root.resolve()).with_suffix("")
    parts = [part for part in relative.parts if part != "__init__"]
    return ".".join(parts) if parts else path.stem


def function_id(path: Path, root: Path, qualname: str) -> str:
    module_name = module_name_for_file(path, root)
    return f"{module_name}.{qualname}" if module_name else qualname


def flowtrace_source_root() -> Path:
    return Path(__file__).resolve().parent

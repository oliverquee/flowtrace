import json
import os
from pathlib import Path

from worker import build_message


def load_name() -> str:
    return os.environ.get("FLOWTRACE_SAMPLE_NAME", "FlowTrace")


def format_message(name: str) -> str:
    prefix = "Hello"
    unused_value = "static analyzer should flag this"
    return f"{prefix}, {name}!"


def write_audit_line(message: str) -> Path:
    output_dir = Path("flowtrace_output")
    output_dir.mkdir(exist_ok=True)
    audit_path = output_dir / "sample_project_side_effect.txt"
    audit_path.write_text(message, encoding="utf-8")
    return audit_path


def unused_helper(value: int) -> int:
    doubled = value * 2
    return doubled


def risky_unused_delete(target: str) -> None:
    Path(target).unlink()


def main() -> Path:
    name = load_name()
    message = format_message(name)
    worker_message = build_message(name)
    print(message)
    print(worker_message)
    return write_audit_line(message)


if __name__ == "__main__":
    main()

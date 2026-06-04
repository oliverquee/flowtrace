"""Command line interface for FlowTrace."""

from __future__ import annotations

import argparse
from pathlib import Path

from .engine import FlowTraceError, analyze_entry, write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trace a Python entry file.")
    parser.add_argument("--entry", required=True, help="Python file to analyze.")
    parser.add_argument(
        "--output-dir",
        default="flowtrace_output",
        help="Directory for generated trace output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = analyze_entry(args.entry)
        written_files = write_outputs(result, args.output_dir)
    except FlowTraceError as exc:
        parser.exit(status=1, message=f"flowtrace: {exc}\n")

    for path in written_files:
        print(f"Generated {Path(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

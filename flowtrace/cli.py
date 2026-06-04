"""Command line interface for FlowTrace."""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from .diagnostics import build_diagnostics
from .graph_builder import build_runtime_graph, build_static_graph
from .intended_flow import compare_intended_flow
from .report_writer import write_reports
from .runtime_tracer import run_with_trace, skipped_runtime_result
from .static_analyzer import analyze_project
from .utils import FlowTraceError, resolve_entry_path, resolve_output_dir, resolve_project_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze and run a Python entry file.")
    parser.add_argument("--entry", required=True, help="Python file to analyze.")
    parser.add_argument(
        "--project-root",
        help="Project root to scan. Defaults to the parent folder of --entry.",
    )
    parser.add_argument(
        "--output",
        default="flowtrace_output",
        help="Directory for generated FlowTrace reports.",
    )
    parser.add_argument(
        "--intended-flow",
        help="Optional JSON file describing expected runtime function order.",
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Analyze only; do not execute the target script.",
    )
    parser.add_argument(
        "--target-args",
        default="",
        help="Arguments to pass to the target script, parsed without shell execution.",
    )
    parser.add_argument("--output-dir", dest="output", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        entry_path = resolve_entry_path(args.entry)
        project_root = resolve_project_root(entry_path, args.project_root)
        output_dir = resolve_output_dir(args.output)

        static_result = analyze_project(project_root, entry_path)
        try:
            target_args = shlex.split(args.target_args) if args.target_args else []
        except ValueError as exc:
            raise FlowTraceError(f"Could not parse --target-args: {exc}") from exc
        if args.static_only:
            runtime_result = skipped_runtime_result(
                entry_path,
                project_root,
                "Static-only mode requested",
                target_args,
            )
        else:
            runtime_result = run_with_trace(entry_path, project_root, target_args)
        intended_comparison = compare_intended_flow(args.intended_flow, runtime_result)
        diagnostics = build_diagnostics(static_result, runtime_result)
        static_graph = build_static_graph(static_result, diagnostics)
        runtime_graph = build_runtime_graph(runtime_result)
        written_files = write_reports(
            output_dir=output_dir,
            entry_path=entry_path,
            project_root=project_root,
            static_result=static_result,
            runtime_result=runtime_result,
            diagnostics=diagnostics,
            static_graph=static_graph,
            runtime_graph=runtime_graph,
            intended_comparison=intended_comparison,
        )
    except FlowTraceError as exc:
        parser.exit(status=1, message=f"flowtrace: {exc}\n")

    for path in written_files:
        print(f"Generated {Path(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

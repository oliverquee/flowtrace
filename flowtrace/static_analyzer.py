"""AST-based static analysis for FlowTrace."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from .utils import flowtrace_source_root, function_id, is_relative_to, iter_python_files, module_name_for_file, relative_path


SIDE_EFFECT_CALLS = {
    "print",
    "input",
    "open",
    "os.remove",
    "os.unlink",
    "os.rename",
    "os.replace",
    "os.rmdir",
    "os.makedirs",
    "os.mkdir",
    "shutil.rmtree",
    "subprocess.call",
    "subprocess.Popen",
    "subprocess.run",
    "sys.exit",
}

SIDE_EFFECT_SUFFIXES = (
    ".append",
    ".clear",
    ".close",
    ".extend",
    ".mkdir",
    ".remove",
    ".rename",
    ".replace",
    ".rmdir",
    ".send",
    ".unlink",
    ".update",
    ".write",
    ".write_bytes",
    ".write_text",
)


@dataclass(frozen=True)
class ImportRecord:
    file: str
    module: str
    name: str
    alias: str | None
    line: int
    used_name: str


@dataclass(frozen=True)
class FunctionRecord:
    id: str
    name: str
    qualname: str
    file: str
    line: int
    args: list[str]


@dataclass(frozen=True)
class CallRecord:
    name: str
    file: str
    line: int
    in_function: str | None
    resolved_function_id: str | None = None


@dataclass(frozen=True)
class AssignmentRecord:
    name: str
    file: str
    line: int
    in_function: str | None


@dataclass(frozen=True)
class VariableReadRecord:
    name: str
    file: str
    line: int
    in_function: str | None


@dataclass(frozen=True)
class ReturnRecord:
    file: str
    line: int
    in_function: str | None
    has_value: bool


@dataclass(frozen=True)
class SideEffectRecord:
    category: str
    call: str
    file: str
    line: int
    in_function: str | None


@dataclass
class FileStaticAnalysis:
    path: str
    module: str
    imports: list[ImportRecord] = field(default_factory=list)
    functions: list[FunctionRecord] = field(default_factory=list)
    calls: list[CallRecord] = field(default_factory=list)
    assignments: list[AssignmentRecord] = field(default_factory=list)
    variable_reads: list[VariableReadRecord] = field(default_factory=list)
    returns: list[ReturnRecord] = field(default_factory=list)
    side_effects: list[SideEffectRecord] = field(default_factory=list)


@dataclass
class StaticAnalysisResult:
    project_root: str
    files: list[FileStaticAnalysis]

    @property
    def imports(self) -> list[ImportRecord]:
        return [item for file in self.files for item in file.imports]

    @property
    def functions(self) -> list[FunctionRecord]:
        return [item for file in self.files for item in file.functions]

    @property
    def calls(self) -> list[CallRecord]:
        return [item for file in self.files for item in file.calls]

    @property
    def assignments(self) -> list[AssignmentRecord]:
        return [item for file in self.files for item in file.assignments]

    @property
    def variable_reads(self) -> list[VariableReadRecord]:
        return [item for file in self.files for item in file.variable_reads]

    @property
    def returns(self) -> list[ReturnRecord]:
        return [item for file in self.files for item in file.returns]

    @property
    def side_effects(self) -> list[SideEffectRecord]:
        return [item for file in self.files for item in file.side_effects]


def analyze_project(project_root: Path, entry_path: Path | None = None) -> StaticAnalysisResult:
    files: list[FileStaticAnalysis] = []
    target_is_flowtrace = bool(entry_path and is_relative_to(entry_path, flowtrace_source_root()))
    for path in iter_python_files(project_root, exclude_flowtrace_source=not target_is_flowtrace):
        files.append(_analyze_file(path, project_root))
    result = StaticAnalysisResult(project_root=str(project_root), files=files)
    _resolve_local_calls(result)
    return result


def _analyze_file(path: Path, project_root: Path) -> FileStaticAnalysis:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    analysis = FileStaticAnalysis(
        path=relative_path(path, project_root),
        module=module_name_for_file(path, project_root),
    )
    _StaticVisitor(path, project_root, analysis).visit(tree)
    return analysis


class _StaticVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, project_root: Path, analysis: FileStaticAnalysis) -> None:
        self.path = path
        self.project_root = project_root
        self.analysis = analysis
        self.scope_stack: list[str] = []

    @property
    def current_function(self) -> str | None:
        if not self.scope_stack:
            return None
        return function_id(self.path, self.project_root, ".".join(self.scope_stack))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            used_name = alias.asname or alias.name.split(".", 1)[0]
            self.analysis.imports.append(
                ImportRecord(
                    file=self.analysis.path,
                    module=alias.name,
                    name=alias.name,
                    alias=alias.asname,
                    line=node.lineno,
                    used_name=used_name,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = "." * node.level + (node.module or "")
        for alias in node.names:
            used_name = alias.asname or alias.name
            self.analysis.imports.append(
                ImportRecord(
                    file=self.analysis.path,
                    module=module,
                    name=alias.name,
                    alias=alias.asname,
                    line=node.lineno,
                    used_name=used_name,
                )
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function(node)

    def visit_Return(self, node: ast.Return) -> None:
        self.analysis.returns.append(
            ReturnRecord(
                file=self.analysis.path,
                line=node.lineno,
                in_function=self.current_function,
                has_value=node.value is not None,
            )
        )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._record_assignment_targets(target, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._record_assignment_targets(node.target, node.lineno)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._record_assignment_targets(node.target, node.lineno)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._record_assignment_targets(node.target, node.lineno)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self._record_assignment_targets(item.optional_vars, node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.analysis.variable_reads.append(
                VariableReadRecord(
                    name=node.id,
                    file=self.analysis.path,
                    line=node.lineno,
                    in_function=self.current_function,
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _call_name(node.func)
        call = CallRecord(
            name=call_name,
            file=self.analysis.path,
            line=node.lineno,
            in_function=self.current_function,
        )
        self.analysis.calls.append(call)
        if _is_side_effect_call(call_name):
            self.analysis.side_effects.append(
                SideEffectRecord(
                    category=_side_effect_category(call_name),
                    call=call_name,
                    file=self.analysis.path,
                    line=node.lineno,
                    in_function=self.current_function,
                )
            )
        self.generic_visit(node)

    def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.scope_stack.append(node.name)
        qualname = ".".join(self.scope_stack)
        self.analysis.functions.append(
            FunctionRecord(
                id=function_id(self.path, self.project_root, qualname),
                name=node.name,
                qualname=qualname,
                file=self.analysis.path,
                line=node.lineno,
                args=_argument_names(node.args),
            )
        )
        self.generic_visit(node)
        self.scope_stack.pop()

    def _record_assignment_targets(self, target: ast.AST, line: int) -> None:
        for name in _assigned_names(target):
            self.analysis.assignments.append(
                AssignmentRecord(
                    name=name,
                    file=self.analysis.path,
                    line=line,
                    in_function=self.current_function,
                )
            )


def _argument_names(args: ast.arguments) -> list[str]:
    names = [arg.arg for arg in args.posonlyargs + args.args + args.kwonlyargs]
    if args.vararg is not None:
        names.append(f"*{args.vararg.arg}")
    if args.kwarg is not None:
        names.append(f"**{args.kwarg.arg}")
    return names


def _assigned_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in target.elts:
            names.extend(_assigned_names(element))
        return names
    if isinstance(target, ast.Attribute):
        return [_call_name(target)]
    return []


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    if isinstance(node, ast.Subscript):
        return _call_name(node.value)
    return "<unknown>"


def _is_side_effect_call(call_name: str) -> bool:
    return call_name in SIDE_EFFECT_CALLS or call_name.endswith(SIDE_EFFECT_SUFFIXES)


def _side_effect_category(call_name: str) -> str:
    if call_name in {"print", "input"}:
        return "console_output"
    if call_name == "open" or call_name.endswith((".open", ".write", ".write_text", ".write_bytes")):
        return "file_write"
    if call_name in {"os.remove", "os.unlink", "shutil.rmtree"} or call_name.endswith(
        (".unlink", ".remove", ".rmtree")
    ):
        return "file_delete"
    if call_name.startswith("subprocess."):
        return "process"
    if call_name.endswith((".append", ".update", ".clear", ".extend")):
        return "state_mutation"
    return "other_side_effect"


def _resolve_local_calls(result: StaticAnalysisResult) -> None:
    functions_by_file_name = {
        (function.file, function.name): function.id for function in result.functions
    }
    functions_by_module_name = {
        (file.module, function.name): function.id
        for file in result.files
        for function in file.functions
        if function.qualname == function.name
    }
    modules = {file.module for file in result.files}
    import_maps = {
        file.path: _local_import_map(file, modules, functions_by_module_name)
        for file in result.files
    }

    for file in result.files:
        resolved_calls: list[CallRecord] = []
        for call in file.calls:
            resolved_calls.append(
                CallRecord(
                    name=call.name,
                    file=call.file,
                    line=call.line,
                    in_function=call.in_function,
                    resolved_function_id=_resolve_call_id(
                        call.name,
                        file.path,
                        functions_by_file_name,
                        functions_by_module_name,
                        import_maps[file.path],
                    ),
                )
            )
        file.calls = resolved_calls


def _local_import_map(
    file: FileStaticAnalysis,
    modules: set[str],
    functions_by_module_name: dict[tuple[str, str], str],
) -> dict[str, str]:
    imports: dict[str, str] = {}
    for item in file.imports:
        if item.module in modules and (item.module, item.name) in functions_by_module_name:
            imports[item.used_name] = functions_by_module_name[(item.module, item.name)]
        elif item.module in modules:
            imports[item.used_name] = item.module
    return imports


def _resolve_call_id(
    call_name: str,
    file_path: str,
    functions_by_file_name: dict[tuple[str, str], str],
    functions_by_module_name: dict[tuple[str, str], str],
    import_map: dict[str, str],
) -> str | None:
    if "." not in call_name:
        if (file_path, call_name) in functions_by_file_name:
            return functions_by_file_name[(file_path, call_name)]
        mapped = import_map.get(call_name)
        if mapped and "." in mapped:
            return mapped
        return None

    module_alias, function_name = call_name.rsplit(".", 1)
    mapped_module = import_map.get(module_alias)
    if mapped_module and (mapped_module, function_name) in functions_by_module_name:
        return functions_by_module_name[(mapped_module, function_name)]
    if (module_alias, function_name) in functions_by_module_name:
        return functions_by_module_name[(module_alias, function_name)]
    return None

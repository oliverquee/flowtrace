from flowtrace_mvp.backend.tracer import trace_code


def edge_changes(result):
    merged = {}
    for edge in result["edges"]:
        merged.update(edge.get("changed_vars", {}))
    return merged


def test_assignment_trace_changed_values():
    result = trace_code("x = 5\ny = x + 2\n")
    changes = edge_changes(result)
    assert changes["x"] == "5"
    assert changes["y"] == "7"
    assert result["error"] is None


def test_if_branch_trace_marks_big_branch():
    code = "x = 10\nif x > 5:\n    y = 'big'\nelse:\n    y = 'small'\n"
    result = trace_code(code)
    changes = edge_changes(result)
    executed_lines = {edge["from_line"] for edge in result["edges"]} | {edge["to_line"] for edge in result["edges"]}
    assert changes["y"] == "'big'"
    assert 3 in executed_lines
    assert 5 not in executed_lines


def test_loop_trace_final_total():
    code = "total = 0\nfor i in range(3):\n    total += i\n"
    result = trace_code(code)
    changes = edge_changes(result)
    assert changes["total"] == "3"
    assert any(edge["from_line"] == 3 and edge["to_line"] == 2 for edge in result["edges"])
    assert result["error"] is None

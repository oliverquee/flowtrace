from flowtrace_mvp.backend.graph_builder import build_graph_model
from flowtrace_mvp.backend.tracer import trace_code


def graph_for(code):
    result = trace_code(code)
    return build_graph_model(code, result["trace_events"])


def node_by_line(graph, line):
    return next(node for node in graph["nodes"] if node["line"] == line)


def test_assignment_code_creates_nodes_and_executed_edge_events():
    graph = graph_for("x = 5\ny = x + 2\n")

    assert graph["nodes"]
    assert node_by_line(graph, 1)["type"] == "assignment"
    assert node_by_line(graph, 1)["executed"] is True

    executed_edges = [edge for edge in graph["edges"] if edge["is_executed"]]
    assert executed_edges
    assert any(edge["events"] for edge in executed_edges)


def test_if_else_code_creates_condition_node_and_if_group():
    code = "x = 10\nif x > 5:\n    y = 'big'\nelse:\n    y = 'small'\n"
    graph = graph_for(code)

    assert node_by_line(graph, 2)["type"] == "condition"
    assert any(group["type"] == "if_block" for group in graph["groups"])


def test_loop_code_compresses_repeated_edges_and_records_count():
    code = "total = 0\nfor i in range(3):\n    total += i\n"
    graph = graph_for(code)

    loop_edges = [edge for edge in graph["edges"] if edge["source"] == "n_3" and edge["target"] == "n_2"]
    assert loop_edges
    assert loop_edges[0]["execution_count"] > 1
    assert len(loop_edges[0]["events"]) == loop_edges[0]["execution_count"]


def test_function_definition_creates_function_group():
    code = "def add(a, b):\n    result = a + b\n    return result\n\nvalue = add(2, 3)\n"
    graph = graph_for(code)

    function_groups = [group for group in graph["groups"] if group["type"] == "function"]
    assert function_groups
    assert function_groups[0]["label"].startswith("def add")


def test_non_executed_branch_node_exists_but_is_not_executed():
    code = "x = 10\nif x > 5:\n    y = 'big'\nelse:\n    y = 'small'\n"
    graph = graph_for(code)

    small_branch = node_by_line(graph, 5)
    assert small_branch["executed"] is False


def test_changed_variable_event_format_is_before_after_object():
    graph = graph_for("x = 5\ny = x + 2\n")

    event_with_x = None
    for edge in graph["edges"]:
        for event in edge["events"]:
            if "x" in event["changed_vars"]:
                event_with_x = event
                break
        if event_with_x:
            break

    assert event_with_x is not None
    assert event_with_x["changed_vars"]["x"] == {"before": "(new)", "after": "5"}

import flowtrace_mvp.backend.app as app_module


def graph_response(code):
    return app_module.graph(app_module.TraceRequest(code=code))


def test_health_route_is_registered_and_returns_ok():
    health_routes = [
        route
        for route in app_module.app.routes
        if getattr(route, "path", None) == "/health" and "GET" in getattr(route, "methods", set())
    ]

    assert health_routes
    assert app_module.health() == {"status": "ok"}


def test_cors_allows_vite_frontend_origins():
    cors_middleware = next(
        middleware for middleware in app_module.app.user_middleware if middleware.cls.__name__ == "CORSMiddleware"
    )

    assert "http://127.0.0.1:5173" in cors_middleware.kwargs["allow_origins"]
    assert "http://localhost:5173" in cors_middleware.kwargs["allow_origins"]


def test_trace_request_accepts_code_only():
    request = app_module.TraceRequest(code="x = 5\n")

    assert request.code == "x = 5\n"
    assert request.stdin == ""


def test_trace_request_accepts_code_plus_stdin():
    request = app_module.TraceRequest(code="name = input()\n", stdin="Pratham\n")

    assert request.code == "name = input()\n"
    assert request.stdin == "Pratham\n"


def test_graph_route_is_registered():
    graph_routes = [
        route
        for route in app_module.app.routes
        if getattr(route, "path", None) == "/api/graph" and "POST" in getattr(route, "methods", set())
    ]

    assert graph_routes


def test_graph_endpoint_returns_graph_sections():
    response = graph_response("x = 5\ny = x + 2\n")

    graph = response["graph"]
    assert set(graph) == {"nodes", "edges", "groups"}
    assert graph["nodes"]
    assert graph["edges"]
    assert isinstance(graph["groups"], list)


def test_graph_endpoint_preserves_stdout():
    response = graph_response("print('hello graph')\nx = 5\n")

    assert response["stdout"] == "hello graph\n"


def test_graph_endpoint_returns_runtime_errors_clearly():
    response = graph_response("x = 1\nraise ValueError('boom')\ny = 2\n")

    error = response["error"]
    assert error["type"] == "ValueError"
    assert error["message"] == "boom"


def test_graph_endpoint_returns_timeout_errors_clearly(monkeypatch):
    original_runner = app_module.run_trace_subprocess

    def short_timeout_runner(code):
        return original_runner(code, timeout_seconds=0.5)

    monkeypatch.setattr(app_module, "run_trace_subprocess", short_timeout_runner)
    response = graph_response("while True:\n    pass\n")

    error = response["error"]
    assert error["type"] == "TimeoutError"
    assert "timed out" in error["message"]


def test_trace_endpoint_still_returns_trace_events():
    response = app_module.trace(app_module.TraceRequest(code="x = 5\ny = x + 2\n"))

    assert response["trace_events"]
    assert response["error"] is None

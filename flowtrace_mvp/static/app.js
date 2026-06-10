const codeInput = document.querySelector("#code-input");
const runButton = document.querySelector("#run-trace");
const loadSampleButton = document.querySelector("#load-sample");
const sampleSelect = document.querySelector("#sample-select");
const graphEl = document.querySelector("#graph");
const inspectorEl = document.querySelector("#inspector");
const pathPanelEl = document.querySelector("#path-panel");
const statusEl = document.querySelector("#status");
const summaryEl = document.querySelector("#summary");
const stdoutEl = document.querySelector("#stdout");
const errorEl = document.querySelector("#error");

const SAMPLES = {
  assignment: {
    name: "Assignment",
    code: "x = 5\ny = x + 2\nprint(y)\n",
  },
  if_branch: {
    name: "If branch",
    code: "x = 10\nif x > 5:\n    y = 'big'\nelse:\n    y = 'small'\nprint(y)\n",
  },
  loop: {
    name: "Loop",
    code: "total = 0\nfor i in range(3):\n    total += i\nprint(total)\n",
  },
  runtime_error: {
    name: "Runtime error",
    code: "x = 5\ny = x / 0\nprint(y)\n",
  },
  timeout: {
    name: "Timeout",
    code: "while True:\n    pass\n",
  },
};

let lastTrace = null;
let selectedEdgeId = null;
let sourceLines = [];

function setStatus(message) {
  statusEl.textContent = message;
}

function setupSamples() {
  for (const [id, sample] of Object.entries(SAMPLES)) {
    const option = document.createElement("option");
    option.value = id;
    option.textContent = sample.name;
    sampleSelect.appendChild(option);
  }
  sampleSelect.value = "assignment";
}

function loadSelectedSample() {
  const sample = SAMPLES[sampleSelect.value] || SAMPLES.assignment;
  codeInput.value = sample.code;
  setStatus(`${sample.name} sample loaded.`);
}

function formatValueMap(values) {
  const entries = Object.entries(values || {});
  if (entries.length === 0) {
    return "No visible variable changes on this transition.";
  }
  return entries.map(([key, value]) => `${key} = ${value}`).join("\n");
}

function changedVariableNames(edge) {
  return Object.keys(edge.changed_vars || {});
}

function sourceForLine(lineNumber) {
  if (!lineNumber || lineNumber < 1 || lineNumber > sourceLines.length) {
    return "";
  }
  return sourceLines[lineNumber - 1];
}

function isLoopBack(edge) {
  return Number(edge.to_line) < Number(edge.from_line);
}

function renderInspector(edge) {
  inspectorEl.classList.remove("empty");
  inspectorEl.innerHTML = "";

  const title = document.createElement("h3");
  title.textContent = `line ${edge.from_line} -> line ${edge.to_line}`;

  const details = document.createElement("dl");
  details.className = "inspector-grid";
  const rows = [
    ["Event id", edge.event_id],
    ["From line", edge.from_line],
    ["To line", edge.to_line],
    ["From source", sourceForLine(edge.from_line) || "(not available)"],
    ["To source", sourceForLine(edge.to_line) || "(not available)"],
    ["Terminal edge", edge.terminal ? "Yes" : "No"],
    ["Loop-back edge", isLoopBack(edge) ? "Yes" : "No"],
  ];
  for (const [label, value] of rows) {
    const term = document.createElement("dt");
    term.textContent = label;
    const description = document.createElement("dd");
    description.textContent = String(value);
    details.append(term, description);
  }

  const changedTitle = document.createElement("h4");
  changedTitle.textContent = "Changed variables";
  const changed = document.createElement("pre");
  changed.textContent = formatValueMap(edge.changed_vars);

  const localsTitle = document.createElement("h4");
  localsTitle.textContent = "Locals snapshot";
  const locals = document.createElement("pre");
  locals.textContent = formatValueMap((lastTrace.trace_events || [])[edge.event_id]?.locals_snapshot || {});

  const stdoutTitle = document.createElement("h4");
  stdoutTitle.textContent = "Stdout at this moment";
  const stdout = document.createElement("pre");
  stdout.textContent = ((lastTrace.trace_events || [])[edge.event_id]?.stdout || "").trim() || "None";

  inspectorEl.append(title, details, changedTitle, changed, localsTitle, locals, stdoutTitle, stdout);
}

function nodeById(nodes) {
  return Object.fromEntries(nodes.map((node) => [node.id, node]));
}

function edgeById(edges) {
  return Object.fromEntries(edges.map((edge) => [edge.id, edge]));
}

function clearSelection() {
  selectedEdgeId = null;
  document.querySelectorAll(".edge.selected, .path-row.selected").forEach((item) => {
    item.classList.remove("selected");
  });
  document.querySelectorAll(".node.node-source, .node.node-target").forEach((node) => {
    node.classList.remove("node-source", "node-target");
  });
}

function selectEdge(edgeId) {
  const edge = edgeById(lastTrace.edges || [])[edgeId];
  if (!edge) {
    return;
  }
  clearSelection();
  selectedEdgeId = edgeId;
  document.querySelectorAll(`[data-edge-id="${CSS.escape(edgeId)}"]`).forEach((item) => {
    item.classList.add("selected");
  });
  const sourceEl = document.getElementById(edge.source);
  const targetEl = document.getElementById(edge.target);
  if (sourceEl) sourceEl.classList.add("node-source");
  if (targetEl) targetEl.classList.add("node-target");
  renderInspector(edge);
}

function renderPath(trace) {
  const edges = trace.edges || [];
  pathPanelEl.innerHTML = "";
  pathPanelEl.className = edges.length ? "path-panel" : "path-panel empty";
  if (edges.length === 0) {
    pathPanelEl.textContent = "No runtime edges captured.";
    return;
  }

  const list = document.createElement("ol");
  list.className = "path-list";
  for (const edge of edges) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "path-row";
    button.dataset.edgeId = edge.id;

    const changedNames = changedVariableNames(edge);
    const changedLabel = changedNames.length ? changedNames.join(", ") : "no vars";
    const stdoutLabel = ((trace.trace_events || [])[edge.event_id]?.stdout || "") ? "stdout" : "";
    button.textContent = `line ${edge.from_line} -> ${edge.to_line} | ${changedLabel}${stdoutLabel ? ` | ${stdoutLabel}` : ""}`;
    button.addEventListener("click", () => selectEdge(edge.id));

    item.appendChild(button);
    list.appendChild(item);
  }
  pathPanelEl.appendChild(list);
}

function edgeClasses(edge, target, node) {
  const classes = ["edge"];
  if (edge.id === selectedEdgeId) {
    classes.push("selected");
  }
  if (target && target.line < node.line) {
    classes.push("loop-back");
  }
  if (edge.terminal) {
    classes.push("terminal");
  }
  return classes.join(" ");
}

function edgeLabel(edge, target, node) {
  if (edge.terminal) {
    return `final line ${edge.from_line}`;
  }
  if (target && target.line < node.line) {
    const names = changedVariableNames(edge);
    const varPart = names.length ? ` | ${names[0]}` : "";
    return `loop line ${edge.from_line} -> ${edge.to_line}${varPart}`;
  }
  return `line ${edge.from_line} -> ${edge.to_line}`;
}

function renderGraph(trace) {
  lastTrace = trace;
  selectedEdgeId = null;
  sourceLines = codeInput.value.split(/\r?\n/);
  graphEl.innerHTML = "";
  inspectorEl.className = "inspector empty";
  inspectorEl.textContent = "Click an arrow or execution path row after running a trace.";

  const nodes = trace.nodes || [];
  const edges = trace.edges || [];
  const nodesById = nodeById(nodes);

  summaryEl.textContent = `${nodes.length} blocks - ${edges.length} runtime arrows`;
  stdoutEl.textContent = trace.stdout || "";
  errorEl.textContent = trace.error ? JSON.stringify(trace.error, null, 2) : "";
  renderPath(trace);

  if (nodes.length === 0) {
    graphEl.textContent = "No executable nodes found.";
    return;
  }

  const edgeGroups = new Map();
  for (const edge of edges) {
    if (!edgeGroups.has(edge.source)) {
      edgeGroups.set(edge.source, []);
    }
    edgeGroups.get(edge.source).push(edge);
  }

  for (const node of nodes) {
    const block = document.createElement("div");
    block.className = `node ${node.executed ? "executed" : "not-executed"}`;
    block.id = node.id;

    const line = document.createElement("div");
    line.className = "node-line";
    line.textContent = `Line ${node.line} - ${node.type}${node.executed ? " - executed" : " - not executed"}`;

    const label = document.createElement("code");
    label.textContent = node.label;

    block.append(line, label);
    graphEl.appendChild(block);

    const outgoing = edgeGroups.get(node.id) || [];
    for (const edge of outgoing) {
      const target = nodesById[edge.target];
      const arrow = document.createElement("button");
      arrow.className = edgeClasses(edge, target, node);
      arrow.type = "button";
      arrow.dataset.edgeId = edge.id;
      arrow.textContent = edgeLabel(edge, target, node);
      arrow.addEventListener("click", () => selectEdge(edge.id));
      graphEl.appendChild(arrow);
    }
  }
}

async function runTrace() {
  setStatus("Running trace...");
  runButton.disabled = true;
  try {
    const response = await fetch("/api/trace", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: codeInput.value }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(JSON.stringify(payload.detail || payload, null, 2));
    }
    renderGraph(payload);
    setStatus(payload.error ? `Trace completed with ${payload.error.type}.` : "Trace complete.");
  } catch (error) {
    setStatus(`Trace failed: ${error.message}`);
  } finally {
    runButton.disabled = false;
  }
}

setupSamples();
loadSampleButton.addEventListener("click", loadSelectedSample);
sampleSelect.addEventListener("change", loadSelectedSample);
runButton.addEventListener("click", runTrace);

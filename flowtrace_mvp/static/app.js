const codeInput = document.querySelector("#code-input");
const runButton = document.querySelector("#run-trace");
const loadSampleButton = document.querySelector("#load-sample");
const graphEl = document.querySelector("#graph");
const inspectorEl = document.querySelector("#inspector");
const statusEl = document.querySelector("#status");
const summaryEl = document.querySelector("#summary");
const stdoutEl = document.querySelector("#stdout");
const errorEl = document.querySelector("#error");

let lastTrace = null;

function setStatus(message) {
  statusEl.textContent = message;
}

function formatValueMap(values) {
  const entries = Object.entries(values || {});
  if (entries.length === 0) {
    return "No visible variable changes on this transition.";
  }
  return entries.map(([key, value]) => `${key} = ${value}`).join("\n");
}

function renderInspector(edge) {
  inspectorEl.classList.remove("empty");
  inspectorEl.innerHTML = "";

  const title = document.createElement("h3");
  title.textContent = `line ${edge.from_line} -> line ${edge.to_line}`;

  const meta = document.createElement("p");
  meta.textContent = `event ${edge.event_id}${edge.terminal ? " - terminal snapshot" : ""}`;

  const values = document.createElement("pre");
  values.textContent = formatValueMap(edge.changed_vars);

  inspectorEl.append(title, meta, values);
}

function nodeById(nodes) {
  return Object.fromEntries(nodes.map((node) => [node.id, node]));
}

function renderGraph(trace) {
  lastTrace = trace;
  graphEl.innerHTML = "";
  inspectorEl.className = "inspector empty";
  inspectorEl.textContent = "Click an arrow after running a trace.";

  const nodes = trace.nodes || [];
  const edges = trace.edges || [];
  const nodesById = nodeById(nodes);

  summaryEl.textContent = `${nodes.length} blocks - ${edges.length} runtime arrows`;
  stdoutEl.textContent = trace.stdout || "";
  errorEl.textContent = trace.error ? JSON.stringify(trace.error, null, 2) : "";

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
    line.textContent = `Line ${node.line} - ${node.type}`;

    const label = document.createElement("code");
    label.textContent = node.label;

    block.append(line, label);
    graphEl.appendChild(block);

    const outgoing = edgeGroups.get(node.id) || [];
    for (const edge of outgoing) {
      const target = nodesById[edge.target];
      const arrow = document.createElement("button");
      arrow.className = "edge";
      arrow.type = "button";
      arrow.textContent = `down line ${edge.from_line} -> ${edge.to_line}`;
      if (target && target.line < node.line) {
        arrow.textContent = `loop line ${edge.from_line} -> ${edge.to_line}`;
      }
      if (edge.terminal) {
        arrow.textContent = `final line ${edge.from_line}`;
      }
      arrow.addEventListener("click", () => renderInspector(edge));
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
    setStatus("Trace complete.");
  } catch (error) {
    setStatus(`Trace failed: ${error.message}`);
  } finally {
    runButton.disabled = false;
  }
}

async function loadSample() {
  const response = await fetch("/api/sample");
  const payload = await response.json();
  codeInput.value = payload.code;
  setStatus("Sample loaded.");
}

runButton.addEventListener("click", runTrace);
loadSampleButton.addEventListener("click", loadSample);

import { Handle, Position } from "@xyflow/react";

const GROUP_ICONS = {
  loop: "⟳",
  function: "⤵",
  if_block: "⬡",
};

const STATUS_LABELS = {
  completed: "✓ completed",
  error: "✗ error",
  not_executed: "— skipped",
};

function formatVars(vars = []) {
  return vars.length > 0 ? vars.join(", ") : "—";
}

export default function GroupNode({ data = {}, id }) {
  const {
    type = "function",
    label = "Group",
    execution_count: executionCount = 0,
    input_vars: inputVars = [],
    output_vars: outputVars = [],
    status = "not_executed",
    isExpanded = false,
    onToggle,
  } = data;
  const groupId = data.id ?? id;
  const className = [
    "group-node",
    `group-node--${type}`,
    isExpanded ? "group-node--expanded" : "group-node--collapsed",
  ].join(" ");

  function handleToggle() {
    if (onToggle) {
      onToggle(groupId);
    }
  }

  return (
    <section className={className} data-group-id={groupId}>
      <Handle type="target" position={Position.Top} className="group-node__handle" />
      <header className="group-node__header">
        <div className="group-node__title">
          <span className="group-node__icon">{GROUP_ICONS[type] ?? "⬡"}</span>
          <span>{label}</span>
        </div>
        <span className={`group-node__status group-node__status--${status}`}>
          {STATUS_LABELS[status] ?? STATUS_LABELS.not_executed}
        </span>
      </header>
      <p className="group-node__stats">
        ran {executionCount}x · in: {formatVars(inputVars)} · out: {formatVars(outputVars)}
      </p>
      <button type="button" className="group-node__toggle" onClick={handleToggle}>
        {isExpanded ? "⊖ collapse" : "⊕ expand"}
      </button>
      <Handle type="source" position={Position.Bottom} className="group-node__handle" />
    </section>
  );
}

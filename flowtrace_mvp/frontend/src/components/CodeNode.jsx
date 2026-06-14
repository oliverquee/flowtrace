import { Handle, Position } from "@xyflow/react";

const MAX_CODE_LENGTH = 40;

function truncateCode(code) {
  if (code.length <= MAX_CODE_LENGTH) {
    return code;
  }
  return `${code.slice(0, MAX_CODE_LENGTH - 3)}...`;
}

export default function CodeNode({ data = {}, id }) {
  const {
    line,
    code = "",
    type = "call",
    executed = false,
    execution_count: executionCount = 0,
  } = data;
  const nodeId = data.id ?? id;
  const isTinted = type === "condition" || type === "loop_header";
  const className = [
    "code-node",
    executed ? "code-node--executed" : "code-node--skipped",
    isTinted ? "code-node--tinted" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className} title={code} data-node-id={nodeId}>
      <Handle type="target" position={Position.Top} className="code-node__handle" />
      <div className="code-node__meta">
        <span>line {line}</span>
        {executionCount > 1 ? <span className="code-node__badge">ran {executionCount}x</span> : null}
      </div>
      <pre className="code-node__code">{truncateCode(code)}</pre>
      <Handle type="source" position={Position.Bottom} className="code-node__handle" />
    </div>
  );
}

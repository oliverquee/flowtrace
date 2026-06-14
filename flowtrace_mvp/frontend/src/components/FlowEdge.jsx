import { BaseEdge, EdgeLabelRenderer, getBezierPath } from "@xyflow/react";

export default function FlowEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  data = {},
}) {
  const {
    execution_count: executionCount = 0,
    is_executed: isExecuted = false,
    isHighlighted = false,
    onEdgeClick,
  } = data;
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });
  const stroke = isHighlighted ? "#7DB7FF" : isExecuted ? "var(--edge-active)" : "var(--edge-inactive)";
  const strokeWidth = isHighlighted ? 3 : isExecuted ? 2 : 1;
  const strokeDasharray = isExecuted ? undefined : "6 5";

  function handleClick() {
    if (onEdgeClick) {
      onEdgeClick(id);
    }
  }

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{ stroke, strokeWidth, strokeDasharray, cursor: "pointer" }}
        onClick={handleClick}
      />
      <path className="flow-edge__hitbox" d={edgePath} onClick={handleClick} />
      {executionCount > 1 ? (
        <EdgeLabelRenderer>
          <button
            type="button"
            className="flow-edge__badge"
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
            onClick={handleClick}
          >
            {executionCount}x
          </button>
        </EdgeLabelRenderer>
      ) : null}
    </>
  );
}

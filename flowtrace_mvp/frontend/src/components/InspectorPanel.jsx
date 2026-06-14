import { useEffect, useState } from "react";

function shortValue(value) {
  const text = String(value ?? "");
  return text.length > 30 ? `${text.slice(0, 27)}...` : text;
}

export default function InspectorPanel({ edge, onClose }) {
  const events = edge?.events ?? [];
  const latestPassIndex = events.length > 0 ? events.length - 1 : 0;
  const [selectedPassIndex, setSelectedPassIndex] = useState(latestPassIndex);

  useEffect(() => {
    setSelectedPassIndex(latestPassIndex);
  }, [edge?.id, latestPassIndex]);

  if (!edge) {
    return null;
  }

  const selectedEvent = events[selectedPassIndex] ?? events[0] ?? {};
  const changedVars = Object.entries(selectedEvent.changed_vars ?? {});

  return (
    <aside className="inspector-panel">
      <header className="inspector-panel__header">
        <h2>{edge.source} -&gt; {edge.target}</h2>
        <button type="button" className="inspector-panel__close" onClick={onClose} aria-label="Close inspector">
          ×
        </button>
      </header>

      {edge.execution_count > 1 ? (
        <div className="inspector-panel__tabs">
          {events.map((event, index) => (
            <button
              type="button"
              className={index === selectedPassIndex ? "inspector-panel__tab is-active" : "inspector-panel__tab"}
              key={event.pass ?? index}
              onClick={() => setSelectedPassIndex(index)}
            >
              Pass {event.pass ?? index + 1}
            </button>
          ))}
        </div>
      ) : null}

      <section className="inspector-panel__section">
        <h3>Changed variables</h3>
        {changedVars.length > 0 ? (
          <table className="inspector-panel__table">
            <thead>
              <tr>
                <th>Variable</th>
                <th>Before</th>
                <th>After</th>
              </tr>
            </thead>
            <tbody>
              {changedVars.map(([name, change]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td title={String(change.before ?? "")}>{shortValue(change.before)}</td>
                  <td title={String(change.after ?? "")}>{shortValue(change.after)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="inspector-panel__empty">—</p>
        )}
      </section>

      {selectedEvent.stdout ? (
        <section className="inspector-panel__section">
          <h3>Stdout</h3>
          <pre className="inspector-panel__pre">{selectedEvent.stdout}</pre>
        </section>
      ) : null}

      {selectedEvent.error ? <p className="inspector-panel__error">{selectedEvent.error}</p> : null}
    </aside>
  );
}

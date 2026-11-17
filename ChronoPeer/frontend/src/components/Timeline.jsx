import { useEffect, useRef } from "react";

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/** Plotly scatter of the events that have a UTC time. Events without one stay in the table only. */
export default function Timeline({ events }) {
  const ref = useRef(null);
  const placed = events.filter((e) => e.event_time_utc);

  useEffect(() => {
    let alive = true;
    import("plotly.js-basic-dist-min").then((mod) => {
      if (!alive || !ref.current) return;
      const Plotly = mod.default || mod;
      const css = getComputedStyle(document.documentElement);
      const color = (name) => css.getPropertyValue(name).trim();
      const types = [...new Set(placed.map((e) => e.event_type))];
      Plotly.react(
        ref.current,
        [
          {
            type: "scatter",
            mode: "markers",
            x: placed.map((e) => e.event_time_utc),
            y: placed.map((e) => e.event_type),
            text: placed.map((e) => `<b>${esc(e.artifact_reference)}</b><br>${esc(e.description).slice(0, 140)}`),
            hovertemplate: "%{text}<br>%{x}<extra></extra>",
            marker: { size: 12, color: color("--accent"), line: { width: 2, color: color("--page") } },
          },
        ],
        {
          height: Math.max(260, 70 + types.length * 44),
          margin: { l: 190, r: 24, t: 12, b: 44 },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          font: { color: color("--ink"), family: "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif", size: 12 },
          xaxis: { type: "date", gridcolor: color("--line"), zeroline: false },
          yaxis: { categoryorder: "array", categoryarray: types.slice().reverse(), gridcolor: color("--line"), automargin: true },
          hoverlabel: { bgcolor: color("--surface"), font: { color: color("--ink") } },
        },
        { responsive: true, displayModeBar: false },
      );
    });
    return () => {
      alive = false;
    };
  }, [events]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!placed.length) {
    return <p className="text-muted">No events have a known or assumed UTC time, so there is nothing to plot. They are listed below.</p>;
  }
  return (
    <div>
      <div ref={ref} role="img" aria-label={`Timeline chart of ${placed.length} events by type and UTC time`} />
      {placed.length < events.length && (
        <p className="mt-2 text-sm text-muted">
          {events.length - placed.length} event(s) have no UTC time (unknown timezone, or a missing or invalid timestamp) and are shown in the table only.
        </p>
      )}
    </div>
  );
}

import { useState } from "react";
import { api } from "../services/api";
import { Btn, Chip } from "./ui";

export default function EvidenceTable({ evidence }) {
  const [results, setResults] = useState({});
  const verify = async (id) => {
    let result;
    try {
      result = (await api.verifyEvidence(id)).result;
    } catch (e) {
      result = e.message;
    }
    setResults((r) => ({ ...r, [id]: result }));
  };
  if (!evidence.length) return <p className="text-muted">No evidence has been imported into this investigation yet.</p>;
  return (
    <div className="scroll-x">
      <table className="w-full min-w-[640px] border-collapse text-left text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-wider text-muted">
            {["File", "Type", "Records", "Imported", "SHA-256", "Integrity"].map((h) => (
              <th key={h} className="border-b border-line px-3 py-2 font-semibold">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {evidence.map((e) => (
            <tr key={e.id} className="align-top">
              <td className="border-b border-line px-3 py-3 font-medium">{e.filename}</td>
              <td className="border-b border-line px-3 py-3">{e.file_type}</td>
              <td className="border-b border-line px-3 py-3">{e.record_count}</td>
              <td className="border-b border-line px-3 py-3 text-muted">{e.imported_at.replace("T", " ").replace("Z", " UTC")}</td>
              <td className="border-b border-line px-3 py-3 font-mono text-xs [overflow-wrap:anywhere]" title={e.sha256}>{e.sha256}</td>
              <td className="border-b border-line px-3 py-3">
                {results[e.id] ? (
                  <Chip kind={results[e.id] === "MATCH" ? "ok" : "bad"}>{results[e.id]}</Chip>
                ) : (
                  <Btn variant="ghost" onClick={() => verify(e.id)}>Re-check</Btn>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

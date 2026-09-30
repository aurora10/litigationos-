"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function LogsPage() {
  const [entries, setEntries] = useState<any[]>([]);
  const [level, setLevel] = useState<string>("");
  const token = () => localStorage.getItem("access_token") ?? "";

  async function load() {
    const q = level ? `?level=${level}` : "";
    const r = await fetch(`${API}/api/logs${q}`, { headers: { Authorization: `Bearer ${token()}` } });
    if (r.ok) setEntries((await r.json()).entries || []);
  }
  useEffect(() => { load(); }, [level]);

  return (
    <main style={{ fontFamily: "monospace", padding: "1.5rem", maxWidth: 1100, margin: "0 auto" }}>
      <h1>Logs</h1>
      <p>
        <a href="/">← cases</a> ·
        Filter: <select value={level} onChange={e => setLevel(e.target.value)}>
          <option value="">all</option><option value="error">error</option>
          <option value="warn">warn</option><option value="info">info</option>
        </select>
        <button onClick={load}>refresh</button>
      </p>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr><th align="left">time</th><th align="left">level</th><th align="left">scope</th><th align="left">event</th><th align="left">detail</th></tr></thead>
        <tbody>
          {entries.map((e, i) => (
            <tr key={i}>
              <td>{e.ts}</td><td>{e.level}</td><td>{e.scope}</td><td>{e.event}</td>
              <td style={{ wordBreak: "break-all" }}>{e.path ?? ""} {e.status ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}

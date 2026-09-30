"use client";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function CasePage({ params }: { params: { id: string } }) {
  const caseId = params.id;
  const [brief, setBrief] = useState<any>(null);
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([]);
  const [input, setInput] = useState("");
  const [analysis, setAnalysis] = useState<any>(null);
  const [drafts, setDrafts] = useState<any[]>([]);
  const [docs, setDocs] = useState<any[]>([]);
  const [error, setError] = useState("");

  const token = () => localStorage.getItem("access_token") ?? "";

  async function upload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files) return;
    for (const f of Array.from(e.target.files)) {
      const fd = new FormData(); fd.append("file", f);
      const r = await fetch(`${API}/api/cases/${caseId}/documents`, {
        method: "POST", headers: { Authorization: `Bearer ${token()}` }, body: fd,
      });
      if (!r.ok) setError(`upload ${f.name}: ${r.status}`);
    }
    await loadDocs();
  }

  async function loadDocs() {
    const r = await fetch(`${API}/api/cases/${caseId}/documents`, { headers: { Authorization: `Bearer ${token()}` } });
    if (r.ok) setDocs(await r.json());
  }

  async function send() {
    const text = input.trim(); if (!text) return;
    setMessages(m => [...m, { role: "you", text }]); setInput("");
    const r = await fetch(`${API}/api/agent/tasks`, {
      method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token()}` },
      body: JSON.stringify({ case_id: caseId, instruction: text }),
    });
    const j = await r.json();
    const t = await fetch(`${API}/api/agent/tasks/${j.id}`, { headers: { Authorization: `Bearer ${token()}` } });
    const out = (await t.json()).output ?? "(no output)";
    setMessages(m => [...m, { role: "agent", text: out }]);
  }

  async function analyze() {
    const r = await fetch(`${API}/api/agent/tasks`, {
      method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token()}` },
      body: JSON.stringify({ case_id: caseId, instruction: "prepare lawyer meeting" }),
    });
    const j = await r.json();
    const t = await fetch(`${API}/api/agent/tasks/${j.id}`, { headers: { Authorization: `Bearer ${token()}` } });
    setAnalysis((await t.json()).output);
  }

  async function listDrafts() {
    const r = await fetch(`${API}/api/cases/${caseId}/drafts`, { headers: { Authorization: `Bearer ${token()}` } });
    if (r.ok) setDrafts(await r.json());
  }

  async function approve(draftId: string, approve: boolean) {
    const to = prompt("Send to (email):", "advocaat@example.be")!;
    const subject = prompt("Subject:", "Update dossier")!;
    // find approval id
    const sub = await fetch(`${API}/api/drafts/${draftId}/submit?to=${encodeURIComponent(to)}&subject=${encodeURIComponent(subject)}`, {
      method: "POST", headers: { Authorization: `Bearer ${token()}` },
    });
    if (!sub.ok) { setError("submit failed"); return; }
    const { approval_id } = await sub.json();
    const r = await fetch(`${API}/api/approvals/${approval_id}/${approve ? "approve" : "reject"}`, {
      method: "POST", headers: { Authorization: `Bearer ${token()}` },
    });
    if (r.ok) listDrafts();
  }

  return (
    <main style={{ fontFamily: "sans-serif", padding: "1.5rem", maxWidth: 1100, margin: "0 auto" }}>
      <h1>Case</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}

      <section style={{ border: "1px solid #ccc", padding: "1rem", marginBottom: "1rem" }}>
        <h2>1. Tell the agent what's going on</h2>
        <textarea rows={3} value={input} onChange={e => setInput(e.target.value)}
          placeholder="Describe the problem in plain language — e.g. 'Mijn verhuurder weigert de waarborg terug te betalen…'"
          style={{ width: "100%" }} />
        <button onClick={send} disabled={!input}>Ask</button>
        <div style={{ marginTop: "1rem" }}>
          {messages.map((m, i) => <p key={i} style={{ whiteSpace: "pre-wrap" }}><b>{m.role}:</b> {m.text}</p>)}
        </div>
      </section>

      <section style={{ border: "1px solid #ccc", padding: "1rem", marginBottom: "1rem" }}>
        <h2>2. Attach your evidence <button onClick={loadDocs}>refresh</button></h2>
        <input type="file" multiple onChange={upload} />
        <ul>{docs.map((d: any) => <li key={d.id}>{d.filename} — {d.processing_status}</li>)}</ul>
      </section>

      <section style={{ border: "1px solid #ccc", padding: "1rem", marginBottom: "1rem" }}>
        <h2>3. Analysis
        <button onClick={analyze}>Generate</button>
        <button onClick={() => navigator.clipboard.writeText(analysis ?? "")}>Copy</button></h2>
        <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f6", padding: "1rem" }}>{analysis ?? "(run Generate)"}</pre>
      </section>

      <section style={{ border: "1px solid #ccc", padding: "1rem" }}>
        <h2>4. Letters to your lawyer <button onClick={listDrafts}>refresh</button></h2>
        <ul>
          {drafts.map((d: any) => (
            <li key={d.id}>
              <b>{d.kind}</b> — <i>{d.status}</i>
              {d.status === "DRAFT" && <> <button onClick={() => approve(d.id, true)}>Approve</button> <button onClick={() => approve(d.id, false)}>Reject</button></>}
              <details><summary>view</summary><pre style={{ whiteSpace: "pre-wrap" }}>{d.body}</pre></details>
            </li>
          ))}
        </ul>
        <p><small>Approve/reject under Inbox → Approvals in the API for now; button UI in the next iteration.</small></p>
      </section>
    </main>
  );
}

"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [health, setHealth] = useState<any>(null);
  const [cases, setCases] = useState<any[] | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API}/health`).then(r => r.json()).then(setHealth).catch(() => setHealth({ status: "unreachable" }));
    const t = localStorage.getItem("access_token");
    if (t) loadCases();
  }, []);

  const token = () => localStorage.getItem("access_token") ?? "";

  async function login(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const email = (form.elements.namedItem("email") as HTMLInputElement).value;
    const password = (form.elements.namedItem("password") as HTMLInputElement).value;
    const r = await fetch(`${API}/api/auth/login`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!r.ok) { setError("login failed"); return; }
    const j = await r.json();
    localStorage.setItem("access_token", j.access_token);
    setError(""); loadCases();
  }

  async function loadCases() {
    const r = await fetch(`${API}/api/cases`, { headers: { Authorization: `Bearer ${token()}` } });
    if (r.status === 401) { setCases(null); return; }
    setCases(await r.json());
  }

  async function createCase() {
    await fetch(`${API}/api/cases`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token()}` },
      body: JSON.stringify({ title }),
    });
    setTitle(""); loadCases();
  }

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem", maxWidth: 800, margin: "0 auto" }}>
      <h1>LitigationOS</h1>
      <p style={{ color: "#666" }}>Backend: <code>{health?.status ?? "…"}</code></p>

      {cases === null ? (
        <form onSubmit={login}>
          <h2>Log in</h2>
          <p><input name="email" placeholder="email" defaultValue="owner@localhost.dev" /></p>
          <p><input name="password" type="password" placeholder="password" /></p>
          <button type="submit">Log in</button>
          {error && <p style={{ color: "red" }}>{error}</p>}
        </form>
      ) : (
        <>
          <h2>Cases</h2>
          <ul>
            {cases.map((c: any) => (
              <li key={c.id}><a href={`/cases/${c.id}`}>{c.title}</a> — {c.status}</li>
            ))}
          </ul>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="New case title" />
          <button onClick={createCase} disabled={!title}>Create</button>
        </>
      )}

      <p style={{ marginTop: "2rem" }}><a href="/logs">Logs</a></p>
    </main>
  );
}

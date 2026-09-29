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
  }, []);

  const token = () => localStorage.getItem("access_token") ?? "";

  async function login() {
    const email = prompt("email", "owner@localhost.dev")!;
    const password = prompt("password")!;
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
    <main style={{ fontFamily: "sans-serif", padding: "2rem", maxWidth: 720, margin: "0 auto" }}>
      <h1>LitigationOS</h1>
      <p>Backend: <code>{JSON.stringify(health)}</code></p>
      <button onClick={login}>Log in</button>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <h2>Cases</h2>
      <p><button onClick={loadCases}>Refresh</button></p>
      {cases === null ? <p><i>Log in to view cases.</i></p> : (
        <>
          <ul>{cases.map((c: any) => <li key={c.id}>{c.title} — {c.status}</li>)}</ul>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="New case title" />
          <button onClick={createCase} disabled={!title}>Create</button>
        </>
      )}
    </main>
  );
}

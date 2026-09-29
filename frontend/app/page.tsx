async function getHealth() {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${base}/health`, { cache: "no-store" });
    return await res.json();
  } catch {
    return { status: "unreachable" };
  }
}

export default async function Home() {
  const health = await getHealth();
  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>LitigationOS</h1>
      <p>Backend health:</p>
      <pre>{JSON.stringify(health, null, 2)}</pre>
    </main>
  );
}

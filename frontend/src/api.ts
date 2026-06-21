import type { Facts } from "./types";

export async function getFacts(): Promise<Facts> {
  const r = await fetch("/facts");
  if (!r.ok) throw new Error(`/facts -> HTTP ${r.status}`);
  return r.json();
}

export interface AskResult {
  ok: boolean;
  answer?: string;
  model?: string;
  error?: string;
}

// Posts to /ask. Never fabricates: surfaces the server's error (e.g. prime
// unreachable -> 503) rather than inventing an answer.
export async function ask(question: string): Promise<AskResult> {
  try {
    const r = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const d = await r.json();
    return r.ok
      ? { ok: true, answer: d.answer, model: d.model }
      : { ok: false, error: d.error || `HTTP ${r.status}` };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

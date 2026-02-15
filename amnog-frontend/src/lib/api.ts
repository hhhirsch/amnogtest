import type { RunResponse, ShortlistResponse } from "./types";
import type { ShortlistRequestInput } from "./validators";

const API_BASE =
  (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/+$/, "") ||
  "https://amnogtest.onrender.com";

export async function createShortlist(payload: ShortlistRequestInput): Promise<ShortlistResponse> {
  const res = await fetch(`${API_BASE}/api/shortlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Shortlist failed (${res.status}): ${await res.text()}`);
  }
  return res.json();
}

export async function getRun(runId: string): Promise<RunResponse> {
  const res = await fetch(`${API_BASE}/api/run/${encodeURIComponent(runId)}`);

  if (!res.ok) {
    throw new Error(`Run lookup failed (${res.status}): ${await res.text()}`);
  }
  return res.json();
}

export async function createLead(runId: string, email: string, company?: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/leads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId, email, company, consent: true }),
  });

  if (!res.ok) {
    throw new Error(`Lead failed (${res.status}): ${await res.text()}`);
  }
}

export async function downloadPdf(runId: string): Promise<Blob> {
  // Backend: @app.get("/api/export/pdf") => Frontend muss GET sein
  const res = await fetch(`${API_BASE}/api/export/pdf?run_id=${encodeURIComponent(runId)}`, {
    method: "GET",
  });

  if (!res.ok) {
    throw new Error(`PDF export failed (${res.status}): ${await res.text()}`);
  }
  return res.blob();
}
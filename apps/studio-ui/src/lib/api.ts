const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface RunPayload {
  task: string;
  target_repo: string;
  thread_id: string;
  max_builder_loops?: number;
  max_architect_loops?: number;
}

export interface ResumePayload {
  thread_id: string;
  approved: boolean;
  instructions?: string;
}

async function postSSE(
  path: string,
  body: unknown,
  signal: AbortSignal,
): Promise<Response> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `${path} failed: ${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`,
    );
  }
  return res;
}

export function runTask(payload: RunPayload, signal: AbortSignal) {
  return postSSE("/api/run", payload, signal);
}

export function resumeTask(payload: ResumePayload, signal: AbortSignal) {
  return postSSE("/api/resume", payload, signal);
}

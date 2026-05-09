/**
 * Parse an SSE stream coming from a fetch() Response into an async iterator
 * of decoded JSON event payloads.
 *
 * We can't use the browser's EventSource here because studio-api's SSE
 * endpoints are POST (with a JSON body), and EventSource only supports GET.
 */
export async function* readSSE<T = unknown>(
  response: Response,
  signal?: AbortSignal,
): AsyncGenerator<T> {
  if (!response.body) {
    throw new Error("Response has no body");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      if (signal?.aborted) break;
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by a blank line ("\n\n").
      let sepIndex: number;
      while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, sepIndex);
        buffer = buffer.slice(sepIndex + 2);

        // Each event may have multiple "data:" lines per the SSE spec, but
        // studio-api emits a single one. We concatenate to be safe.
        const dataLines = rawEvent
          .split("\n")
          .filter((l) => l.startsWith("data:"))
          .map((l) => l.slice(5).trimStart());
        if (dataLines.length === 0) continue;
        const payload = dataLines.join("\n");
        try {
          yield JSON.parse(payload) as T;
        } catch {
          // Malformed frame: skip it but keep the stream alive.
          continue;
        }
      }
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // ignore
    }
  }
}

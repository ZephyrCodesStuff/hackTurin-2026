/**
 * Server-side helper to resolve the API Host at runtime.
 * Prioritizes process.env.API_HOST (e.g. "http://api:8000" in Docker),
 * and automatically falls back to 127.0.0.1:8000 for local development.
 */
export async function proxyFetch(path: string, init?: RequestInit): Promise<Response> {
  const preferredHost =
    process.env.API_HOST ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8000";
  try {
    const res = await fetch(`${preferredHost}${path}`, {
      ...init,
      cache: "no-store",
    });
    return res;
  } catch (err: unknown) {
    // If running outside Docker and "api" DNS doesn't resolve, fallback to local host
    if (preferredHost !== "http://127.0.0.1:8000") {
      try {
        return await fetch(`http://127.0.0.1:8000${path}`, {
          ...init,
          cache: "no-store",
        });
      } catch {
        // rethrow original error
      }
    }
    throw err;
  }
}

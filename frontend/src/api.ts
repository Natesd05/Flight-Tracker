export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    let message = `Request failed (${response.status}). Please try again.`;
    try {
      const data = await response.json();
      message = data.error?.message || message;
    } catch {
      /* Non-JSON gateway error */
    }
    throw new Error(message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

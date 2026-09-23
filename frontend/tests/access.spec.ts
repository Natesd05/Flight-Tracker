import { test, expect } from "@playwright/test";

test("demo gate protects pages and API and rejects cross-origin writes", async ({ playwright, request, baseURL }) => {
  test.skip(!process.env.E2E_AUTH_PASSWORD, "Requires the protected demo proxy.");
  const anonymous = await playwright.request.newContext({
    baseURL,
    httpCredentials: undefined,
    ignoreHTTPSErrors: process.env.E2E_ALLOW_SELF_SIGNED === "true",
  });
  try {
    for (const path of ["/", "/api/preferences", "/api/schedule", "/api/saved", "/api/health", ...(process.env.E2E_PUBLIC_LIVENESS === "true" ? [] : ["/healthz"])]) {
      const response = await anonymous.get(path);
      expect(response.status()).toBe(401);
      expect(response.headers()["www-authenticate"]).toContain("Basic");
    }
    if (process.env.E2E_PUBLIC_LIVENESS === "true") {
      expect((await anonymous.get("/healthz")).status()).toBe(200);
    }
    expect((await anonymous.post("/api/searches", { data: {} })).status()).toBe(401);
    expect((await request.get("/api/health")).status()).toBe(200);
    // Empty bodies would get 422 from FastAPI if the proxy failed to reject them.
    for (const headers of [{ Origin: "https://untrusted.example" }, { "Sec-Fetch-Site": "cross-site" }]) {
      const response = await request.post("/api/classes", { headers, data: {} });
      expect(response.status()).toBe(403);
    }
  } finally {
    await anonymous.dispose();
  }
});

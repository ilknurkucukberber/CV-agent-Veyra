import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch, ApiError, clearToken, setToken } from "./api";

describe("apiFetch", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("adds the Authorization header when a token is stored", async () => {
    setToken("test-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/resumes");

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer test-token");
  });

  it("clears the token and throws ApiError(401) on an unauthorized response", async () => {
    setToken("stale-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 401 })),
    );

    await expect(apiFetch("/auth/me")).rejects.toBeInstanceOf(ApiError);
    expect(localStorage.getItem("token")).toBeNull();
  });

  it("surfaces the backend's detail message on failure", async () => {
    clearToken();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "İş ilanı bulunamadı" }), {
          status: 404,
        }),
      ),
    );

    await expect(apiFetch("/job-postings/999")).rejects.toMatchObject({
      status: 404,
      message: "İş ilanı bulunamadı",
    });
  });

  it("explains network failures instead of leaking a raw fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(apiFetch("/auth/register", { method: "POST" })).rejects.toMatchObject({
      status: 0,
      message: "Sunucuya bağlanılamadı. Bağlantını kontrol edip tekrar dene.",
    });
  });

  it("formats validation errors as text that React can render", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: [{ loc: ["body", "password"], msg: "String should have at least 8 characters" }],
    }), { status: 422 })));

    await expect(apiFetch("/auth/register")).rejects.toMatchObject({
      status: 422,
      message: "password: String should have at least 8 characters",
    });
  });

  it("explains proxy errors even when the response is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Bad Gateway", { status: 502 })));

    await expect(apiFetch("/auth/register")).rejects.toMatchObject({
      status: 502,
      message: "Sunucu şu anda isteği tamamlayamıyor. Lütfen biraz sonra tekrar dene.",
    });
  });

  it("preserves explicit request cancellation", async () => {
    const error = new DOMException("Aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(error));

    await expect(apiFetch("/resumes")).rejects.toBe(error);
  });
});

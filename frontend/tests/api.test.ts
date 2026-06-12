import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../src/api";

const BASE = "http://127.0.0.1:8000/api";

function mockFetch(response: unknown, ok = true, status = 200) {
  const fn = vi.fn().mockResolvedValue({
    ok,
    status,
    statusText: ok ? "OK" : "Error",
    json: async () => response,
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.unstubAllGlobals());

describe("api.getEntities", () => {
  it("encodes filter params into the query string", async () => {
    const fetchFn = mockFetch([{ entity_id: "FGI-001" }]);
    await api.getEntities({ jurisdiction: "Spain", status: "Dormant" });
    expect(fetchFn).toHaveBeenCalledWith(
      `${BASE}/entities?jurisdiction=Spain&status=Dormant`,
    );
  });
});

describe("api.triggerDigest", () => {
  it("posts without fresh by default", async () => {
    const fetchFn = mockFetch({ status: "completed" });
    await api.triggerDigest();
    expect(fetchFn).toHaveBeenCalledWith(`${BASE}/digest`, { method: "POST" });
  });

  it("adds ?fresh=true for a live scan", async () => {
    const fetchFn = mockFetch({ status: "completed" });
    await api.triggerDigest(true);
    expect(fetchFn).toHaveBeenCalledWith(`${BASE}/digest?fresh=true`, { method: "POST" });
  });

  it("surfaces the backend detail message on error", async () => {
    mockFetch({ detail: "rate limited" }, false, 429);
    await expect(api.triggerDigest()).rejects.toThrow("rate limited");
  });
});

describe("api chat history", () => {
  it("sends the question and conversation id as JSON", async () => {
    const fetchFn = mockFetch({ conversation_id: "abc", answer: "hi", sources: [] });
    const reply = await api.sendChat("Which are dormant?", "abc");
    expect(fetchFn).toHaveBeenCalledWith(
      `${BASE}/chat`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ question: "Which are dormant?", conversation_id: "abc" }),
      }),
    );
    expect(reply.conversation_id).toBe("abc");
  });

  it("passes null conversation id for a new chat", async () => {
    const fetchFn = mockFetch({ conversation_id: "new", answer: "a", sources: [] });
    await api.sendChat("first question", null);
    const body = JSON.parse((fetchFn.mock.calls[0][1] as RequestInit).body as string);
    expect(body.conversation_id).toBeNull();
  });

  it("deletes a conversation by id", async () => {
    const fetchFn = mockFetch({ deleted: true });
    await api.deleteChat("abc");
    expect(fetchFn).toHaveBeenCalledWith(`${BASE}/chats/abc`, { method: "DELETE" });
  });

  it("throws on a failed GET", async () => {
    mockFetch(null, false, 500);
    await expect(api.listChats()).rejects.toThrow();
  });
});

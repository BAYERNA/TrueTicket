import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { apiClient } from "./api-client";
import { useSessionStore } from "@/store/useSessionStore";

function mockFetchOnce(response: { status: number; body?: unknown }) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: response.status >= 200 && response.status < 300,
      status: response.status,
      statusText: "",
      json: async () => response.body,
    }),
  );
}

const UserSchema = z.object({ id: z.string(), name: z.string() });

describe("apiClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    useSessionStore.getState().logout();
  });

  it("returns parsed data when the response matches the schema", async () => {
    mockFetchOnce({ status: 200, body: { id: "u1", name: "Tester" } });

    const result = await apiClient.get("/api/users/u1", UserSchema);

    expect(result).toEqual({ id: "u1", name: "Tester" });
  });

  it("throws a clear error when the response violates the schema", async () => {
    // 백엔드가 계약을 어기고 name 필드를 빼먹은 경우 — 타입 캐스팅만으로는 컴파일 타임에
    // 잡히지 않고 런타임에 undefined로 조용히 새어나갈 수 있는 케이스.
    mockFetchOnce({ status: 200, body: { id: "u1" } });

    await expect(apiClient.get("/api/users/u1", UserSchema)).rejects.toThrow(
      /API 응답이 예상한 형식과 다릅니다/,
    );
  });

  it("skips validation when no schema is passed (backward compatible)", async () => {
    mockFetchOnce({ status: 200, body: { anything: true } });

    const result = await apiClient.get<{ anything: boolean }>("/api/anything");

    expect(result).toEqual({ anything: true });
  });

  it("throws on a non-2xx response without attempting to parse the body", async () => {
    mockFetchOnce({ status: 409, body: { message: "conflict" } });

    await expect(apiClient.post("/api/reservations", {}, UserSchema)).rejects.toThrow(
      /API request failed: 409/,
    );
  });

  it("logs the session out on a 401 while a token is present", async () => {
    useSessionStore.getState().login({ userId: "u1", email: "a@b.com", roles: ["USER"], accessToken: "token" });
    mockFetchOnce({ status: 401, body: {} });

    await expect(apiClient.get("/api/reservations")).rejects.toThrow();

    expect(useSessionStore.getState().accessToken).toBeNull();
  });

  it("returns undefined for a 204 response without touching the body", async () => {
    mockFetchOnce({ status: 204 });

    const result = await apiClient.post<undefined>("/api/reservations/r1/cancel");

    expect(result).toBeUndefined();
  });
});

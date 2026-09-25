import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it } from "vitest";
import { z } from "zod";
import { apiClient } from "./api-client";
import { server } from "@/test/msw-server";
import { useSessionStore } from "@/store/useSessionStore";

const API_BASE_URL = "http://localhost:8080";
const UserSchema = z.object({ id: z.string(), name: z.string() });

describe("apiClient", () => {
  afterEach(() => {
    useSessionStore.getState().logout();
  });

  it("returns parsed data when the response matches the schema", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/users/u1`, () => HttpResponse.json({ id: "u1", name: "Tester" })),
    );

    const result = await apiClient.get("/api/users/u1", UserSchema);

    expect(result).toEqual({ id: "u1", name: "Tester" });
  });

  it("throws a clear error when the response violates the schema", async () => {
    // 백엔드가 계약을 어기고 name 필드를 빼먹은 경우 — 타입 캐스팅만으로는 컴파일 타임에
    // 잡히지 않고 런타임에 undefined로 조용히 새어나갈 수 있는 케이스.
    server.use(http.get(`${API_BASE_URL}/api/users/u1`, () => HttpResponse.json({ id: "u1" })));

    await expect(apiClient.get("/api/users/u1", UserSchema)).rejects.toThrow(
      /API 응답이 예상한 형식과 다릅니다/,
    );
  });

  it("skips validation when no schema is passed (backward compatible)", async () => {
    server.use(http.get(`${API_BASE_URL}/api/anything`, () => HttpResponse.json({ anything: true })));

    const result = await apiClient.get<{ anything: boolean }>("/api/anything");

    expect(result).toEqual({ anything: true });
  });

  it("rejects on a non-2xx response", async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/reservations`, () =>
        HttpResponse.json({ message: "conflict" }, { status: 409 }),
      ),
    );

    await expect(apiClient.post("/api/reservations", {}, UserSchema)).rejects.toThrow(/409/);
  });

  it("logs the session out on a 401 while a token is present", async () => {
    useSessionStore
      .getState()
      .login({ userId: "u1", email: "a@b.com", roles: ["USER"], accessToken: "token" });
    server.use(http.get(`${API_BASE_URL}/api/reservations`, () => HttpResponse.json({}, { status: 401 })));

    await expect(apiClient.get("/api/reservations")).rejects.toThrow();

    expect(useSessionStore.getState().accessToken).toBeNull();
  });

  it("attaches the bearer token from the session store to every request", async () => {
    useSessionStore
      .getState()
      .login({ userId: "u1", email: "a@b.com", roles: ["USER"], accessToken: "secret-token" });
    let receivedAuthHeader: string | null = null;
    server.use(
      http.get(`${API_BASE_URL}/api/reservations`, ({ request }) => {
        receivedAuthHeader = request.headers.get("authorization");
        return HttpResponse.json([]);
      }),
    );

    await apiClient.get("/api/reservations");

    expect(receivedAuthHeader).toBe("Bearer secret-token");
  });

  it("returns undefined for a 204 response without touching the body", async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/reservations/r1/cancel`, () => new HttpResponse(null, { status: 204 })),
    );

    const result = await apiClient.post<undefined>("/api/reservations/r1/cancel");

    expect(result).toBeUndefined();
  });
});

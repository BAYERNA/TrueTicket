import { afterEach, describe, expect, it } from "vitest";
import { useSessionStore } from "./useSessionStore";

describe("useSessionStore", () => {
  afterEach(() => {
    useSessionStore.getState().logout();
  });

  it("starts logged out", () => {
    const state = useSessionStore.getState();
    expect(state.userId).toBeNull();
    expect(state.accessToken).toBeNull();
    expect(state.roles).toEqual([]);
  });

  it("login sets the full session", () => {
    useSessionStore.getState().login({
      userId: "u1",
      email: "a@b.com",
      roles: ["USER", "STAFF"],
      accessToken: "token-abc",
    });

    const state = useSessionStore.getState();
    expect(state.userId).toBe("u1");
    expect(state.email).toBe("a@b.com");
    expect(state.roles).toEqual(["USER", "STAFF"]);
    expect(state.accessToken).toBe("token-abc");
  });

  it("logout clears the session back to its initial shape", () => {
    useSessionStore.getState().login({
      userId: "u1",
      email: "a@b.com",
      roles: ["USER"],
      accessToken: "token-abc",
    });

    useSessionStore.getState().logout();

    const state = useSessionStore.getState();
    expect(state.userId).toBeNull();
    expect(state.email).toBeNull();
    expect(state.roles).toEqual([]);
    expect(state.accessToken).toBeNull();
  });

  it("persists the session under sessionStorage so it survives a reload but not a new browser session", () => {
    useSessionStore.getState().login({
      userId: "u1",
      email: "a@b.com",
      roles: ["USER"],
      accessToken: "token-abc",
    });

    const raw = sessionStorage.getItem("trueticket-session");
    expect(raw).not.toBeNull();
    expect(JSON.parse(raw!).state.accessToken).toBe("token-abc");
  });
});

import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OAuth2CallbackView } from "./callback-view";
import { useSessionStore } from "@/store/useSessionStore";

let searchParams = new URLSearchParams();
const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => searchParams,
}));

describe("OAuth2CallbackView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.getState().logout();
    searchParams = new URLSearchParams();
  });

  it("logs the user in from the redirect query params and goes to /events", async () => {
    searchParams = new URLSearchParams({
      accessToken: "google-issued-token",
      userId: "u1",
      email: "google-user@example.com",
      role: "USER",
    });

    render(<OAuth2CallbackView />);

    await waitFor(() => {
      expect(useSessionStore.getState().accessToken).toBe("google-issued-token");
    });
    expect(useSessionStore.getState().userId).toBe("u1");
    expect(useSessionStore.getState().roles).toEqual(["USER"]);
    expect(replace).toHaveBeenCalledWith("/events");
  });

  it("sends the user back to /login when the redirect is missing required params", async () => {
    searchParams = new URLSearchParams({ accessToken: "token-without-the-rest" });

    render(<OAuth2CallbackView />);

    await waitFor(() => {
      expect(replace).toHaveBeenCalledWith("/login");
    });
    expect(useSessionStore.getState().accessToken).toBeNull();
  });
});

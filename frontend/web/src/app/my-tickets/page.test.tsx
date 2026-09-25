import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MyTicketsPage from "./page";
import { apiClient } from "@/lib/api-client";
import { useSessionStore } from "@/store/useSessionStore";
import type { ReservationResponse } from "@/types/domain";

vi.mock("@/lib/api-client", () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
}));

const mockedApiClient = vi.mocked(apiClient);

const confirmedReservation: ReservationResponse = {
  reservationId: "res-1",
  userId: "u1",
  eventId: "evt1",
  seatId: "seat-1",
  status: "CONFIRMED",
  qrCode: "QR-CODE-1",
  reservedAt: "2026-01-01T00:00:00Z",
  expiresAt: "2026-01-01T00:15:00Z",
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MyTicketsPage />
    </QueryClientProvider>,
  );
}

describe("MyTicketsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore
      .getState()
      .login({ userId: "u1", email: "a@b.com", roles: ["USER"], accessToken: "token" });
    mockedApiClient.get.mockResolvedValue([confirmedReservation]);
  });

  it("shows a cancel button for a non-cancelled reservation and opens a confirmation dialog", async () => {
    const user = userEvent.setup();
    renderPage();

    const cancelButton = await screen.findByRole("button", { name: "예매 취소" });
    await user.click(cancelButton);

    expect(screen.getByText("예매를 취소할까요?")).toBeInTheDocument();
    expect(mockedApiClient.post).not.toHaveBeenCalled();
  });

  it("calls the cancel endpoint only after confirming in the dialog", async () => {
    const user = userEvent.setup();
    mockedApiClient.post.mockResolvedValue({ ...confirmedReservation, status: "CANCELLED", qrCode: null });
    renderPage();

    await user.click(await screen.findByRole("button", { name: "예매 취소" }));
    await user.click(screen.getByRole("button", { name: "네, 취소합니다" }));

    await waitFor(() => {
      expect(mockedApiClient.post).toHaveBeenCalledWith(
        "/api/reservations/res-1/cancel",
        undefined,
        expect.anything(),
      );
    });
  });

  it("does not render a cancel button for an already-cancelled reservation", async () => {
    mockedApiClient.get.mockResolvedValue([{ ...confirmedReservation, status: "CANCELLED", qrCode: null }]);
    renderPage();

    await screen.findByText("취소됨");
    expect(screen.queryByRole("button", { name: "예매 취소" })).not.toBeInTheDocument();
  });
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReserveView } from "./reserve-view";
import { apiClient } from "@/lib/api-client";
import { useSessionStore } from "@/store/useSessionStore";
import type { QueueStatusResponse, Seat } from "@/types/domain";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/api-client", () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
}));

const mockedApiClient = vi.mocked(apiClient);

const admittedQueueStatus: QueueStatusResponse = {
  eventId: "evt1",
  userId: "u1",
  rank: 0,
  waitingCount: 0,
  admitted: true,
};

const seats: Seat[] = [
  { id: "seat-1", eventId: "evt1", seatSection: "A", seatRow: "1", seatNumber: 1, price: 50000, status: "AVAILABLE" },
  { id: "seat-2", eventId: "evt1", seatSection: "A", seatRow: "1", seatNumber: 2, price: 50000, status: "SOLD" },
];

function renderReserveView() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ReserveView eventId="evt1" />
    </QueryClientProvider>,
  );
}

describe("ReserveView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.getState().login({ userId: "u1", email: "a@b.com", roles: ["USER"], accessToken: "token" });

    mockedApiClient.post.mockImplementation((path: string) => {
      if (path.endsWith("/join")) return Promise.resolve(admittedQueueStatus);
      return Promise.resolve(undefined);
    });
    mockedApiClient.get.mockImplementation((path: string) => {
      if (path.includes("/status")) return Promise.resolve(admittedQueueStatus);
      if (path.includes("/seats")) return Promise.resolve(seats);
      return Promise.resolve(undefined);
    });
  });

  it("disables a seat that isn't AVAILABLE and keeps the confirm button off without a selection", async () => {
    renderReserveView();

    const soldSeatButton = await screen.findByRole("button", { name: /A 1-2/ });
    expect(soldSeatButton).toBeDisabled();

    const confirmButton = screen.getByRole("button", { name: "좌석 확정하기" });
    expect(confirmButton).toBeDisabled();
  });

  it("selects an available seat on click and enables the confirm button", async () => {
    const user = userEvent.setup();
    renderReserveView();

    const availableSeatButton = await screen.findByRole("button", { name: /A 1-1/ });
    await user.click(availableSeatButton);

    expect(availableSeatButton.className).toContain("bg-blue-700");
    expect(screen.getByRole("button", { name: "좌석 확정하기" })).toBeEnabled();
  });

  it("submits the reservation with the seat, event, and session id on confirm", async () => {
    const user = userEvent.setup();
    renderReserveView();

    const availableSeatButton = await screen.findByRole("button", { name: /A 1-1/ });
    await user.click(availableSeatButton);
    await user.click(screen.getByRole("button", { name: "좌석 확정하기" }));

    await waitFor(() => {
      expect(mockedApiClient.post).toHaveBeenCalledWith(
        "/api/reservations",
        expect.objectContaining({ eventId: "evt1", seatId: "seat-1" }),
        expect.anything(),
      );
    });
  });
});

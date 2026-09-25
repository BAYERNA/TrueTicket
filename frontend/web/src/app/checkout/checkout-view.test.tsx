import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CheckoutView } from "./checkout-view";
import { apiClient } from "@/lib/api-client";
import type { PaymentResponse } from "@/types/domain";

let searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useSearchParams: () => searchParams,
}));

vi.mock("@/lib/api-client", () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
}));

const mockedApiClient = vi.mocked(apiClient);

const pendingPayment: PaymentResponse = {
  paymentId: "pay-1",
  reservationId: "res-1",
  providerPaymentId: "mock_provider",
  amount: 50000,
  status: "PENDING",
  reservationExpiresAt: new Date().toISOString(),
  mockCheckoutToken: "mock_provider",
};

function renderCheckoutView() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <CheckoutView />
    </QueryClientProvider>,
  );
}

describe("CheckoutView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchParams = new URLSearchParams();
  });

  it("shows a clear message when no reservationId is present", () => {
    renderCheckoutView();

    expect(screen.getByText("예매 번호가 없습니다.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("prepares payment and shows the amount once prepare succeeds", async () => {
    searchParams = new URLSearchParams({ reservationId: "res-1" });
    mockedApiClient.post.mockResolvedValueOnce(pendingPayment);
    const user = userEvent.setup();

    renderCheckoutView();
    await user.click(screen.getByRole("button", { name: "카드 결제 준비" }));

    expect(await screen.findByText(/50,000원/)).toBeInTheDocument();
    expect(mockedApiClient.post).toHaveBeenCalledWith(
      "/api/payments/res-1/prepare",
      expect.objectContaining({ paymentMethod: "MOCK_CARD" }),
      expect.anything(),
    );
  });

  it("moves to the paid state and links to my-tickets after mock completion", async () => {
    searchParams = new URLSearchParams({ reservationId: "res-1" });
    mockedApiClient.post.mockResolvedValueOnce(pendingPayment);
    mockedApiClient.post.mockResolvedValueOnce({ ...pendingPayment, status: "PAID" });
    const user = userEvent.setup();

    renderCheckoutView();
    await user.click(screen.getByRole("button", { name: "카드 결제 준비" }));
    await screen.findByRole("button", { name: "모의 결제 승인" });
    await user.click(screen.getByRole("button", { name: "모의 결제 승인" }));

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /결제 완료/ })).toHaveAttribute("href", "/my-tickets");
    });
  });
});

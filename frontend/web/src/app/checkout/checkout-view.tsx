"use client";

import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import type { PaymentResponse } from "@/types/domain";

export function CheckoutView() {
  const searchParams = useSearchParams();
  const reservationId = searchParams.get("reservationId");
  const [payment, setPayment] = useState<PaymentResponse | null>(null);

  const prepare = useMutation({
    mutationFn: () =>
      apiClient.post<PaymentResponse>(`/api/payments/${reservationId}/prepare`, {
        idempotencyKey: crypto.randomUUID(),
        paymentMethod: "MOCK_CARD",
      }),
    onSuccess: setPayment,
  });

  const complete = useMutation({
    mutationFn: () => apiClient.post<PaymentResponse>(`/api/payments/${payment?.paymentId}/mock-complete`),
    onSuccess: setPayment,
  });

  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col gap-6 px-6 py-12">
      <h1 className="text-2xl font-semibold">결제</h1>
      {reservationId ? (
        <>
          <p className="text-sm text-zinc-500">예매 번호: {reservationId}</p>
          {!payment && (
            <button type="button" disabled={prepare.isPending} onClick={() => prepare.mutate()} className="rounded-full bg-blue-700 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50">
              {prepare.isPending ? "결제 준비 중..." : "카드 결제 준비"}
            </button>
          )}
          {payment?.status === "PENDING" && (
            <div className="flex flex-col gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
              <p className="font-medium">결제 금액 {payment.amount.toLocaleString("ko-KR")}원</p>
              <p className="text-xs text-zinc-500">개발 환경의 모의 결제입니다. 운영에서는 PG 결제창과 서명 검증 웹훅으로 대체됩니다.</p>
              <button type="button" disabled={complete.isPending} onClick={() => complete.mutate()} className="rounded-full bg-blue-700 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50">
                {complete.isPending ? "승인 처리 중..." : "모의 결제 승인"}
              </button>
            </div>
          )}
          {payment?.status === "PAID" && (
            <Link href="/my-tickets" className="rounded-full bg-green-700 px-5 py-2.5 text-center text-sm font-medium text-white hover:bg-green-800">
              결제 완료 — 마이 티켓 보기
            </Link>
          )}
          {(prepare.isError || complete.isError) && <p className="text-sm text-red-600">결제를 처리할 수 없습니다. 선점 시간이 만료되었는지 확인해주세요.</p>}
        </>
      ) : (
        <p className="text-sm text-red-600">예매 번호가 없습니다.</p>
      )}
    </div>
  );
}

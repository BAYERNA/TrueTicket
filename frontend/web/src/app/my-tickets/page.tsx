"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useSessionStore } from "@/store/useSessionStore";
import type { ReservationResponse } from "@/types/domain";

// SCR-05: 예매 완료된 티켓의 QR 코드를 확인한다.
export default function MyTicketsPage() {
  const userId = useSessionStore((state) => state.userId);

  const { data: reservations, isPending } = useQuery({
    queryKey: ["my-reservations", userId],
    queryFn: () => apiClient.get<ReservationResponse[]>(`/api/reservations?userId=${userId}`),
    enabled: !!userId,
  });

  if (!userId) {
    return (
      <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 px-6 py-12">
        <p className="text-sm text-zinc-500">티켓을 보려면 먼저 로그인해주세요.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-12">
      <h1 className="text-2xl font-semibold">마이 티켓</h1>

      {isPending && <p className="text-sm text-zinc-500">불러오는 중...</p>}
      {reservations?.length === 0 && (
        <p className="text-sm text-zinc-500">예매 내역이 없습니다.</p>
      )}

      <ul className="flex flex-col gap-4">
        {reservations?.map((reservation) => (
          <li
            key={reservation.reservationId}
            className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
          >
            <p className="text-xs text-zinc-500">{reservation.status}</p>
            <p className="mt-1 font-mono text-sm">{reservation.qrCode}</p>
            <p className="mt-1 text-xs text-zinc-500">
              예매 시각: {new Date(reservation.reservedAt).toLocaleString("ko-KR")}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}

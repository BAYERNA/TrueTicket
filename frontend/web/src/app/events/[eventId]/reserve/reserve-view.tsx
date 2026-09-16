"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { useSessionStore } from "@/store/useSessionStore";
import type { QueueStatusResponse, ReservationResponse, Seat } from "@/types/domain";

export function ReserveView({ eventId }: { eventId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const userId = useSessionStore((state) => state.userId) ?? "anonymous-dev-user";
  const [selectedSeatId, setSelectedSeatId] = useState<string | null>(null);

  // FR-001: 진입 시 가상대기열에 배치하고 실시간 순번을 안내한다.
  const joinQueue = useMutation({
    mutationFn: () =>
      apiClient.post<QueueStatusResponse>(`/api/queue/${eventId}/join`, { userId }),
  });

  useEffect(() => {
    joinQueue.mutate();
    // eventId가 바뀔 때만 재진입한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId]);

  const { data: queueStatus } = useQuery({
    queryKey: ["queue-status", eventId, userId],
    queryFn: () => apiClient.get<QueueStatusResponse>(`/api/queue/${eventId}/status/${userId}`),
    enabled: joinQueue.isSuccess,
    refetchInterval: 3000,
  });

  // FR-002-1: 좌석은 JPA Optimistic Lock으로 보호되므로 목록은 예매 시도 직전까지 최신 상태를 유지해야 한다.
  const { data: seats, isPending: seatsLoading } = useQuery({
    queryKey: ["event-seats", eventId],
    queryFn: () => apiClient.get<Seat[]>(`/api/events/${eventId}/seats`),
    enabled: !queueStatus || queueStatus.admitted !== false,
  });

  const reserve = useMutation({
    mutationFn: (seatId: string) =>
      apiClient.post<ReservationResponse>("/api/reservations", { userId, eventId, seatId }),
    onSuccess: (reservation) => {
      router.push(`/checkout?reservationId=${reservation.reservationId}`);
    },
    onError: () => {
      // 409 Conflict: 다른 사용자가 먼저 선점(Optimistic Lock 충돌)한 좌석.
      setSelectedSeatId(null);
      queryClient.invalidateQueries({ queryKey: ["event-seats", eventId] });
    },
  });

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-12">
      <h1 className="text-2xl font-semibold">좌석 선택</h1>

      {queueStatus && !queueStatus.admitted && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          대기 중입니다. 현재 순번: {queueStatus.rank} / 대기 인원: {queueStatus.waitingCount}
        </div>
      )}

      {seatsLoading && <p className="text-sm text-zinc-500">좌석 정보를 불러오는 중...</p>}

      <div className="grid grid-cols-6 gap-2">
        {seats?.map((seat) => (
          <button
            key={seat.id}
            type="button"
            disabled={seat.status !== "AVAILABLE" || reserve.isPending}
            onClick={() => setSelectedSeatId(seat.id)}
            className={`rounded-md border p-2 text-xs ${
              seat.status !== "AVAILABLE"
                ? "cursor-not-allowed border-zinc-200 bg-zinc-100 text-zinc-400 dark:border-zinc-800 dark:bg-zinc-900"
                : selectedSeatId === seat.id
                  ? "border-blue-700 bg-blue-700 text-white"
                  : "border-zinc-300 hover:border-blue-700 dark:border-zinc-700"
            }`}
          >
            {seat.seatSection} {seat.seatRow}-{seat.seatNumber}
          </button>
        ))}
      </div>

      <button
        type="button"
        disabled={!selectedSeatId || reserve.isPending}
        onClick={() => selectedSeatId && reserve.mutate(selectedSeatId)}
        className="rounded-full bg-blue-700 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
      >
        {reserve.isPending ? "예매 처리 중..." : "좌석 확정하기"}
      </button>

      {reserve.isError && (
        <p className="text-sm text-red-600">이미 선점된 좌석입니다. 다른 좌석을 선택해주세요.</p>
      )}
    </div>
  );
}

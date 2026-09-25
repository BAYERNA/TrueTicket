"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { useSessionStore } from "@/store/useSessionStore";
import { QueueStatusResponseSchema, ReservationResponseSchema, SeatListSchema } from "@/types/domain";

export function ReserveView({ eventId }: { eventId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const userId = useSessionStore((state) => state.userId);
  const [selectedSeatId, setSelectedSeatId] = useState<string | null>(null);
  // FR-003/FR-004: 좌석 선택 화면에 진입한 시점부터 하나의 "예매 세션"으로 간주하고,
  // 행동 로그·취득 부정성 스코어 조회·최종 예매 요청을 모두 이 ID로 묶는다.
  const [reservationSessionId] = useState(() => crypto.randomUUID());
  const lastClickAtRef = useRef<number | null>(null);

  function trackClick() {
    const now = Date.now();
    const intervalMs = lastClickAtRef.current !== null ? now - lastClickAtRef.current : null;
    lastClickAtRef.current = now;

    // 행동 로그 수집은 best-effort: 실패해도 예매 흐름을 막지 않는다.
    apiClient
      .post("/api/bot-detection/behavior-logs", {
        reservationSessionId,
        eventType: "click",
        // metadata는 bot-detection-service의 자유 형식 dict라 스코어링 로직(interval_ms)과
        // 이름을 맞춰야 한다.
        metadata: intervalMs !== null ? { interval_ms: intervalMs } : {},
      })
      .catch(() => undefined);
  }

  // FR-001: 진입 시 가상대기열에 배치하고 실시간 순번을 안내한다.
  const joinQueue = useMutation({
    mutationFn: () =>
      apiClient.post(`/api/queue/${eventId}/join`, undefined, QueueStatusResponseSchema),
  });

  useEffect(() => {
    if (!userId) {
      router.replace("/login");
      return;
    }
    joinQueue.mutate();
    // eventId가 바뀔 때만 재진입한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId, userId]);

  const { data: queueStatus } = useQuery({
    queryKey: ["queue-status", eventId, userId],
    queryFn: () => apiClient.get(`/api/queue/${eventId}/status`, QueueStatusResponseSchema),
    enabled: !!userId && joinQueue.isSuccess,
    refetchInterval: 3000,
  });

  // FR-002-1: 좌석은 JPA Optimistic Lock으로 보호되므로 목록은 예매 시도 직전까지 최신 상태를 유지해야 한다.
  const { data: seats, isPending: seatsLoading } = useQuery({
    queryKey: ["event-seats", eventId],
    queryFn: () => apiClient.get(`/api/events/${eventId}/seats`, SeatListSchema),
    enabled: !queueStatus || queueStatus.admitted !== false,
  });

  const reserve = useMutation({
    mutationFn: (seatId: string) =>
      apiClient.post(
        "/api/reservations",
        { eventId, seatId, reservationSessionId },
        ReservationResponseSchema,
      ),
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
            onClick={() => {
              setSelectedSeatId(seat.id);
              trackClick();
            }}
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
        <p className="text-sm text-red-600">
          {reserve.error instanceof Error && reserve.error.message.includes("403")
            ? "이상 행동이 감지되어 예매가 제한되었습니다."
            : "이미 선점된 좌석입니다. 다른 좌석을 선택해주세요."}
        </p>
      )}
    </div>
  );
}

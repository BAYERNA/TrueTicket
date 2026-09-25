"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useSessionStore } from "@/store/useSessionStore";
import { ReservationListSchema, ReservationResponseSchema, type ReservationResponse } from "@/types/domain";

const STATUS_LABEL: Record<ReservationResponse["status"], string> = {
  PENDING: "결제 대기",
  CONFIRMED: "예매 확정",
  CANCELLED: "취소됨",
};

// SCR-05: 예매 완료된 티켓의 QR 코드를 확인하고, 취소 가능한 예매는 직접 취소할 수 있다.
export default function MyTicketsPage() {
  const userId = useSessionStore((state) => state.userId);
  const queryClient = useQueryClient();
  const [pendingCancelId, setPendingCancelId] = useState<string | null>(null);

  const { data: reservations, isPending } = useQuery({
    queryKey: ["my-reservations", userId],
    queryFn: () => apiClient.get("/api/reservations", ReservationListSchema),
    enabled: !!userId,
  });

  const cancelMutation = useMutation({
    mutationFn: (reservationId: string) =>
      apiClient.post(`/api/reservations/${reservationId}/cancel`, undefined, ReservationResponseSchema),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-reservations", userId] });
      setPendingCancelId(null);
    },
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
      {reservations?.length === 0 && <p className="text-sm text-zinc-500">예매 내역이 없습니다.</p>}

      <ul className="flex flex-col gap-4">
        {reservations?.map((reservation) => (
          <li key={reservation.reservationId}>
            <Card>
              <CardHeader>
                <p className="text-muted-foreground text-xs">{STATUS_LABEL[reservation.status]}</p>
                {reservation.qrCode && <p className="mt-1 font-mono text-sm">{reservation.qrCode}</p>}
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-xs">
                  예매 시각: {new Date(reservation.reservedAt).toLocaleString("ko-KR")}
                </p>
              </CardContent>
              {reservation.status !== "CANCELLED" && (
                <CardFooter>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPendingCancelId(reservation.reservationId)}
                  >
                    예매 취소
                  </Button>
                </CardFooter>
              )}
            </Card>
          </li>
        ))}
      </ul>

      <Dialog open={pendingCancelId !== null} onOpenChange={(open) => !open && setPendingCancelId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>예매를 취소할까요?</DialogTitle>
            <DialogDescription>
              취소하면 좌석이 다시 판매 가능한 상태로 풀리고, 결제된 금액은 환불 처리됩니다. 이 작업은 되돌릴
              수 없습니다.
            </DialogDescription>
          </DialogHeader>
          {cancelMutation.isError && (
            <p className="text-sm text-red-600">취소에 실패했습니다. 잠시 후 다시 시도해주세요.</p>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setPendingCancelId(null)}
              disabled={cancelMutation.isPending}
            >
              닫기
            </Button>
            <Button
              variant="destructive"
              disabled={cancelMutation.isPending}
              onClick={() => pendingCancelId && cancelMutation.mutate(pendingCancelId)}
            >
              {cancelMutation.isPending ? "취소하는 중..." : "네, 취소합니다"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

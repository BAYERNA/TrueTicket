"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useSessionStore } from "@/store/useSessionStore";

interface NotificationItem {
  id: string;
  type: string;
  message: string;
  isRead: boolean;
  createdAt: string;
}

// SCR-12: 판정 결과, 신고 처리 상태 등 개인화된 알림.
export default function NotificationsPage() {
  const userId = useSessionStore((state) => state.userId);

  const { data: notifications, isPending } = useQuery({
    queryKey: ["notifications", userId],
    queryFn: () => apiClient.get<NotificationItem[]>(`/api/notifications?userId=${userId}`),
    enabled: !!userId,
  });

  if (!userId) {
    return (
      <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 px-6 py-12">
        <p className="text-sm text-zinc-500">알림을 보려면 먼저 로그인해주세요.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-12">
      <h1 className="text-2xl font-semibold">알림함</h1>

      {isPending && <p className="text-sm text-zinc-500">불러오는 중...</p>}
      {notifications?.length === 0 && <p className="text-sm text-zinc-500">알림이 없습니다.</p>}

      <ul className="flex flex-col gap-2">
        {notifications?.map((notification) => (
          <li
            key={notification.id}
            className={`rounded-lg border p-4 text-sm ${
              notification.isRead
                ? "border-zinc-200 dark:border-zinc-800"
                : "border-blue-300 bg-blue-50 dark:border-blue-800 dark:bg-blue-950"
            }`}
          >
            <p className="text-xs font-medium text-zinc-500">{notification.type}</p>
            <p className="mt-1">{notification.message}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

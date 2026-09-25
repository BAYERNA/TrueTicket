"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";
import type { TrueTicketEvent } from "@/types/domain";

// SCR-02: 예매 가능한 공연/경기 목록.
export default function EventsPage() {
  const {
    data: events,
    isPending,
    error,
  } = useQuery({
    queryKey: ["events"],
    queryFn: () => apiClient.get<TrueTicketEvent[]>("/api/events"),
  });

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-6 py-12">
      <h1 className="text-2xl font-semibold">이벤트 목록</h1>

      {isPending && <p className="text-sm text-zinc-500">불러오는 중...</p>}
      {error && (
        <p className="text-sm text-red-600">
          이벤트를 불러오지 못했습니다. Gateway/ticket-service가 실행 중인지 확인하세요.
        </p>
      )}

      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {events?.map((event) => (
          <li key={event.id} className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
            <p className="text-xs font-medium text-blue-700 dark:text-blue-400">{event.category}</p>
            <h2 className="mt-1 font-semibold">{event.title}</h2>
            <p className="mt-1 text-sm text-zinc-500">{event.venue}</p>
            <p className="text-sm text-zinc-500">{new Date(event.eventDatetime).toLocaleString("ko-KR")}</p>
            <Link
              href={`/events/${event.id}/reserve`}
              className="mt-3 inline-block text-sm font-medium text-blue-700 hover:underline dark:text-blue-400"
            >
              예매하기 →
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

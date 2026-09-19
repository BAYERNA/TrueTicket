"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";
import type { ResaleListing } from "@/types/domain";

// SCR-07: 운영자가 재판매 게시물 수집 현황과 이상거래를 파악한다.
export default function AdminDashboardPage() {
  const { data: listings, isPending } = useQuery({
    queryKey: ["resale-listings"],
    queryFn: () => apiClient.get<ResaleListing[]>("/api/resale-monitor/listings"),
  });

  const flagged = listings?.filter((l) => l.priceAnomalyScore > 0) ?? [];

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-6 py-12">
      <h1 className="text-2xl font-semibold">재판매 모니터링 대시보드</h1>

      <div className="grid grid-cols-3 gap-4 text-sm">
        <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
          <p className="text-zinc-500">수집된 게시물</p>
          <p className="mt-1 text-2xl font-semibold">{listings?.length ?? "-"}</p>
        </div>
        <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
          <p className="text-zinc-500">이상 가격 의심</p>
          <p className="mt-1 text-2xl font-semibold">{flagged.length}</p>
        </div>
        <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
          <Link href="/admin/bot-logs" className="text-blue-700 hover:underline dark:text-blue-400">
            봇 탐지 로그 보기 →
          </Link>
        </div>
      </div>

      {isPending && <p className="text-sm text-zinc-500">불러오는 중...</p>}

      <table className="w-full text-left text-sm">
        <thead className="text-zinc-500">
          <tr>
            <th className="py-2">플랫폼</th>
            <th className="py-2">공연명</th>
            <th className="py-2">게시 가격</th>
            <th className="py-2">이상치 스코어</th>
            <th className="py-2" />
          </tr>
        </thead>
        <tbody>
          {listings?.map((listing) => (
            <tr key={listing.listingId} className="border-t border-zinc-100 dark:border-zinc-900">
              <td className="py-2">{listing.platformName}</td>
              <td className="py-2">{listing.eventTitleMatched}</td>
              <td className="py-2">{listing.listedPrice.toLocaleString("ko-KR")}원</td>
              <td className="py-2">{listing.priceAnomalyScore.toFixed(2)}</td>
              <td className="py-2">
                <Link
                  href={`/admin/listings/${listing.listingId}`}
                  className="text-blue-700 hover:underline dark:text-blue-400"
                >
                  상세 판정
                </Link>
                {" · "}
                <Link
                  href={`/admin/sellers/${listing.sellerId}`}
                  className="text-blue-700 hover:underline dark:text-blue-400"
                >
                  판매자
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

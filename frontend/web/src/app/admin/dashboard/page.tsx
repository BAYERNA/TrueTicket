"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiClient } from "@/lib/api-client";
import { ResaleListingListSchema } from "@/types/domain";

// SCR-07: 운영자가 재판매 게시물 수집 현황과 이상거래를 파악한다.
export default function AdminDashboardPage() {
  const { data: listings, isPending } = useQuery({
    queryKey: ["resale-listings"],
    queryFn: () => apiClient.get("/api/resale-monitor/listings", ResaleListingListSchema),
  });

  const flagged = listings?.filter((l) => l.priceAnomalyScore > 0) ?? [];

  const platformStats = useMemo(() => {
    const byPlatform = new Map<string, { count: number; scoreSum: number }>();
    for (const listing of listings ?? []) {
      const entry = byPlatform.get(listing.platformName) ?? { count: 0, scoreSum: 0 };
      entry.count += 1;
      entry.scoreSum += listing.priceAnomalyScore;
      byPlatform.set(listing.platformName, entry);
    }
    return Array.from(byPlatform.entries()).map(([platform, { count, scoreSum }]) => ({
      platform,
      count,
      averageScore: count > 0 ? Number((scoreSum / count).toFixed(2)) : 0,
    }));
  }, [listings]);

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

      {platformStats.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
            <p className="mb-2 text-sm text-zinc-500">플랫폼별 게시물 수</p>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={platformStats}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="platform" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" name="게시물 수" fill="var(--primary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
            <p className="mb-2 text-sm text-zinc-500">플랫폼별 평균 이상치 스코어</p>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={platformStats}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="platform" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar
                  dataKey="averageScore"
                  name="평균 이상치 스코어"
                  fill="var(--destructive)"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

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

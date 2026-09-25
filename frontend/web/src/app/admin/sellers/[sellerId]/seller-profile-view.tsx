"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { SellerProfile } from "@/types/domain";

export function SellerProfileView({ sellerId }: { sellerId: string }) {
  const { data: seller, isPending } = useQuery({
    queryKey: ["seller-profile", sellerId],
    queryFn: () => apiClient.get<SellerProfile>(`/api/resale-monitor/sellers/${sellerId}`),
  });

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-12">
      <h1 className="text-2xl font-semibold">판매자 프로파일</h1>

      {isPending && <p className="text-sm text-zinc-500">불러오는 중...</p>}

      {seller && (
        <dl className="grid grid-cols-2 gap-y-3 rounded-lg border border-zinc-200 p-6 text-sm dark:border-zinc-800">
          <dt className="text-zinc-500">플랫폼</dt>
          <dd>{seller.platformName}</dd>
          <dt className="text-zinc-500">판매자 ID(플랫폼 내)</dt>
          <dd>{seller.externalSellerId}</dd>
          <dt className="text-zinc-500">누적 게시 건수</dt>
          <dd>{seller.listingCount}</dd>
          <dt className="text-zinc-500">상습성 스코어</dt>
          <dd>{seller.habitualScore.toFixed(2)}</dd>
        </dl>
      )}
    </div>
  );
}

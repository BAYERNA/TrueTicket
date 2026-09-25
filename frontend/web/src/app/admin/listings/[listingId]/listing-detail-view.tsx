"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { ResaleListing } from "@/types/domain";

export function ListingDetailView({ listingId }: { listingId: string }) {
  const { data: listing, isPending } = useQuery({
    queryKey: ["resale-listing", listingId],
    queryFn: () => apiClient.get<ResaleListing>(`/api/resale-monitor/listings/${listingId}`),
  });

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-12">
      <h1 className="text-2xl font-semibold">이상거래 상세 판정</h1>

      {isPending && <p className="text-sm text-zinc-500">불러오는 중...</p>}

      {listing && (
        <div className="rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <dl className="grid grid-cols-2 gap-y-3 text-sm">
            <dt className="text-zinc-500">플랫폼</dt>
            <dd>{listing.platformName}</dd>
            <dt className="text-zinc-500">공연명</dt>
            <dd>{listing.eventTitleMatched}</dd>
            <dt className="text-zinc-500">게시 가격</dt>
            <dd>{listing.listedPrice.toLocaleString("ko-KR")}원</dd>
            <dt className="text-zinc-500">상습 판매 스코어(가격 이상치)</dt>
            <dd>{listing.priceAnomalyScore.toFixed(2)}</dd>
          </dl>
          <p className="mt-4 text-xs text-zinc-500">
            취득 부정성 스코어와의 AND 판정 결과는 notification-service의 `/api/judgments/session/
            {"{reservationSessionId}"}` 에서 예매 세션 ID로 조회한다. 게시물이 특정 예매 세션과 매칭된
            경우에만 판정 이력이 존재한다.
          </p>
        </div>
      )}
    </div>
  );
}

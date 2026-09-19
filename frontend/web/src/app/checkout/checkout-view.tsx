"use client";

import { useSearchParams } from "next/navigation";
import Link from "next/link";

// TODO: 결제 게이트웨이 연동은 범위 밖. payments 테이블(ticket-service)에 대응하는
// 결제 확정 엔드포인트가 추가되면 이 화면에서 호출한다.
export function CheckoutView() {
  const searchParams = useSearchParams();
  const reservationId = searchParams.get("reservationId");

  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col gap-6 px-6 py-12">
      <h1 className="text-2xl font-semibold">결제</h1>
      {reservationId ? (
        <>
          <p className="text-sm text-zinc-500">예매 번호: {reservationId}</p>
          <p className="text-sm text-zinc-500">결제 수단 연동은 추후 구현 예정입니다.</p>
          <Link
            href="/my-tickets"
            className="rounded-full bg-blue-700 px-5 py-2.5 text-center text-sm font-medium text-white hover:bg-blue-800"
          >
            마이 티켓으로 이동
          </Link>
        </>
      ) : (
        <p className="text-sm text-red-600">예매 번호가 없습니다.</p>
      )}
    </div>
  );
}

import Link from "next/link";

export default function Home() {
  return (
    <div className="mx-auto flex max-w-5xl flex-1 flex-col gap-6 px-6 py-16">
      <p className="text-sm font-medium text-blue-700 dark:text-blue-400">
        예매 → 재판매 → 입장까지, 티켓의 전 생애주기 암표 방지 플랫폼
      </p>
      <h1 className="text-4xl font-semibold tracking-tight">TrueTicket</h1>
      <p className="max-w-2xl text-zinc-600 dark:text-zinc-400">
        취득 부정성 스코어(예매 단계 봇/매크로 탐지)와 상습 판매 스코어(유통 단계 재판매
        이상탐지)를 AND 엔진으로 결합해, 가격만으로 판단하지 않는 암표 판정을 제공합니다.
      </p>
      <div className="flex gap-4">
        <Link
          href="/events"
          className="rounded-full bg-blue-700 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-800"
        >
          예매 가능한 이벤트 보기
        </Link>
        <Link
          href="/admin/dashboard"
          className="rounded-full border border-zinc-300 px-5 py-2.5 text-sm font-medium hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-900"
        >
          운영자 대시보드
        </Link>
      </div>
    </div>
  );
}

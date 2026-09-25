import { ReserveView } from "./reserve-view";

// SCR-03: 가상대기열을 통과한 사용자가 좌석을 선택하고 예매를 요청하는 화면.
export default async function ReservePage({ params }: PageProps<"/events/[eventId]/reserve">) {
  const { eventId } = await params;
  return <ReserveView eventId={eventId} />;
}

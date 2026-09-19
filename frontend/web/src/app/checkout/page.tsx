import { Suspense } from "react";
import { CheckoutView } from "./checkout-view";

// SCR-04: 선택한 좌석에 대한 결제 수단을 선택하고 결제를 완료한다.
export default function CheckoutPage() {
  return (
    <Suspense fallback={<p className="px-6 py-12 text-sm text-zinc-500">불러오는 중...</p>}>
      <CheckoutView />
    </Suspense>
  );
}

import { Suspense } from "react";
import { OAuth2CallbackView } from "./callback-view";

// Google 로그인 성공 후 ticket-service의 OAuth2LoginSuccessHandler가 리다이렉트하는 목적지.
export default function OAuth2CallbackPage() {
  return (
    <div className="mx-auto flex w-full max-w-sm flex-1 flex-col items-center justify-center gap-2 px-6 py-16">
      <Suspense fallback={<p className="text-sm text-zinc-500">로그인 처리 중...</p>}>
        <OAuth2CallbackView />
      </Suspense>
    </div>
  );
}

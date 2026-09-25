import * as Sentry from "@sentry/nextjs";

// NEXT_PUBLIC_SENTRY_DSN이 없으면(로컬/CI 기본값) SDK는 이벤트를 그냥 버리고 조용히
// 비활성 상태로 동작한다 — 실제 운영 배포 시 이 환경변수로 프로젝트 DSN을 주입해야
// 브라우저 에러가 실제로 전송된다.
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
});

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;

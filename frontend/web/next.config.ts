import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs/config";

const nextConfig: NextConfig = {/* config options here */};

export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  silent: true,
  // 소스맵 업로드는 SENTRY_AUTH_TOKEN이 있을 때만 의미가 있고, Turbopack 빌드에서는
  // 어차피 빌드타임 계측이 적용되지 않는다 — 인증 정보 없이도 빌드가 sentry.io에
  // 접근을 시도하지 않도록 명시적으로 끈다.
  sourcemaps: { disable: !process.env.SENTRY_AUTH_TOKEN },
});

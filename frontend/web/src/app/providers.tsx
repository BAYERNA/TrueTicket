"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

let browserQueryClient: QueryClient | undefined;

function getQueryClient() {
  // 서버 렌더링마다 격리된 클라이언트를 새로 만들고, 브라우저에서는 하나를 재사용한다.
  if (typeof window === "undefined") return new QueryClient();
  browserQueryClient ??= new QueryClient();
  return browserQueryClient;
}

export function Providers({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={getQueryClient()}>{children}</QueryClientProvider>;
}

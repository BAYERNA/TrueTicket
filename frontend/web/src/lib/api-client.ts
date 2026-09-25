import type { ZodType } from "zod";
import { useSessionStore } from "@/store/useSessionStore";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

async function request<T>(path: string, options?: RequestInit, schema?: ZodType<T>): Promise<T> {
  const accessToken = useSessionStore.getState().accessToken;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...options?.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401 && accessToken) {
      useSessionStore.getState().logout();
    }
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json();
  if (!schema) {
    return data as T;
  }

  // TypeScript는 컴파일 타임에만 응답 타입을 보장한다. 백엔드가 계약을 어겨도(필드 누락,
  // 타입 변경 등) 조용히 undefined로 새어나가는 대신, 예매/결제처럼 실패 비용이 큰 흐름은
  // 여기서 실제로 검증해 명확한 에러로 실패하게 한다.
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new Error(`API 응답이 예상한 형식과 다릅니다: ${path} — ${result.error.message}`);
  }
  return result.data;
}

/** 모든 요청은 Spring Cloud Gateway(단일 진입점)를 거친다. */
export const apiClient = {
  get: <T>(path: string, schema?: ZodType<T>) => request<T>(path, undefined, schema),
  post: <T>(path: string, body?: unknown, schema?: ZodType<T>) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }, schema),
};

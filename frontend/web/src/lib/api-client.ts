import axios, { AxiosError } from "axios";
import type { ZodType } from "zod";
import { useSessionStore } from "@/store/useSessionStore";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

const httpClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// 매 요청마다 최신 access token을 헤더에 싣는다 — 컴포넌트마다 직접 토큰을 읽어 넣지
// 않도록 공통 인터셉터 한 곳에서 처리한다.
httpClient.interceptors.request.use((config) => {
  const accessToken = useSessionStore.getState().accessToken;
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// 401은 토큰 만료/무효를 뜻하므로 공통으로 세션을 정리한다 — 각 화면이 401을 개별
// 처리할 필요가 없다.
httpClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && useSessionStore.getState().accessToken) {
      useSessionStore.getState().logout();
    }
    return Promise.reject(error);
  },
);

function parse<T>(data: unknown, schema: ZodType<T> | undefined, path: string): T {
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
  get: async <T>(path: string, schema?: ZodType<T>): Promise<T> => {
    const response = await httpClient.get(path);
    return parse(response.data, schema, path);
  },
  post: async <T>(path: string, body?: unknown, schema?: ZodType<T>): Promise<T> => {
    const response = await httpClient.post(path, body);
    if (response.status === 204) {
      return undefined as T;
    }
    return parse(response.data, schema, path);
  },
};

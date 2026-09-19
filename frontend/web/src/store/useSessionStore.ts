import { create } from "zustand";

interface SessionState {
  userId: string | null;
  email: string | null;
  login: (userId: string, email: string) => void;
  logout: () => void;
}

/** SCR-01 로그인 이후 세션 전역에서 공유되는 최소 상태. 토큰 저장은 별도 httpOnly 쿠키/스토리지 전략으로 확장한다. */
export const useSessionStore = create<SessionState>((set) => ({
  userId: null,
  email: null,
  login: (userId, email) => set({ userId, email }),
  logout: () => set({ userId: null, email: null }),
}));

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

interface SessionState {
  userId: string | null;
  email: string | null;
  roles: string[];
  accessToken: string | null;
  login: (session: Omit<SessionState, "login" | "logout">) => void;
  logout: () => void;
}

/** 브라우저 탭이 닫히면 제거되는 세션 스토리지에만 access token을 보관한다. */
export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      userId: null,
      email: null,
      roles: [],
      accessToken: null,
      login: (session) => set(session),
      logout: () => set({ userId: null, email: null, roles: [], accessToken: null }),
    }),
    {
      name: "trueticket-session",
      storage: createJSONStorage(() => sessionStorage),
    },
  ),
);

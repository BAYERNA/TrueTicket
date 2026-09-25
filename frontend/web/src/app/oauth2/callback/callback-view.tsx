"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { useSessionStore } from "@/store/useSessionStore";

export function OAuth2CallbackView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useSessionStore((state) => state.login);

  useEffect(() => {
    const accessToken = searchParams.get("accessToken");
    const userId = searchParams.get("userId");
    const email = searchParams.get("email");
    const role = searchParams.get("role");

    if (!accessToken || !userId || !email || !role) {
      router.replace("/login");
      return;
    }

    login({ userId, email, roles: [role], accessToken });
    router.replace("/events");
  }, [searchParams, login, router]);

  return <p className="text-sm text-zinc-500">로그인 처리 중...</p>;
}

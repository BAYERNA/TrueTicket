"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSessionStore } from "@/store/useSessionStore";
import { AuthResponseSchema } from "@/types/domain";
import Link from "next/link";

interface LoginFormValues {
  email: string;
  password: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

// SCR-01: 이메일/비밀번호를 검증하고 API 호출에 사용할 JWT를 발급받는다.
export default function LoginPage() {
  const router = useRouter();
  const login = useSessionStore((state) => state.login);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>();

  const onSubmit = handleSubmit(async (values) => {
    try {
      const session = await apiClient.post("/api/auth/login", values, AuthResponseSchema);
      login({
        userId: session.userId,
        email: session.email,
        roles: [session.role],
        accessToken: session.accessToken,
      });
      router.replace("/events");
    } catch {
      setError("root", { message: "이메일 또는 비밀번호를 확인해주세요." });
    }
  });

  return (
    <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-6 px-6 py-16">
      <h1 className="text-2xl font-semibold">로그인</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <Label htmlFor="email">이메일</Label>
          <Input id="email" type="email" {...register("email", { required: "이메일을 입력하세요" })} />
          {errors.email && <p className="text-xs text-red-600">{errors.email.message}</p>}
        </div>

        {errors.root && <p className="text-sm text-red-600">{errors.root.message}</p>}

        <div className="flex flex-col gap-1">
          <Label htmlFor="password">비밀번호</Label>
          <Input
            id="password"
            type="password"
            {...register("password", { required: "비밀번호를 입력하세요" })}
          />
          {errors.password && <p className="text-xs text-red-600">{errors.password.message}</p>}
        </div>

        <Button type="submit" disabled={isSubmitting} className="mt-2 rounded-full">
          로그인
        </Button>
      </form>
      <div className="flex items-center gap-3 text-xs text-zinc-400">
        <div className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
        또는
        <div className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
      </div>
      <a
        href={`${API_BASE_URL}/oauth2/authorization/google`}
        className="flex items-center justify-center gap-2 rounded-full border border-zinc-300 px-5 py-2.5 text-sm font-medium hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-900"
      >
        Google로 로그인
      </a>
      <p className="text-center text-sm text-zinc-500">
        계정이 없나요?{" "}
        <Link className="font-medium text-blue-700" href="/register">
          회원가입
        </Link>
      </p>
    </div>
  );
}

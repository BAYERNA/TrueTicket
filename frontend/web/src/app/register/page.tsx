"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { apiClient } from "@/lib/api-client";
import { useSessionStore } from "@/store/useSessionStore";
import type { AuthResponse } from "@/types/domain";

interface RegisterFormValues {
  email: string;
  password: string;
  name: string;
}

export default function RegisterPage() {
  const router = useRouter();
  const login = useSessionStore((state) => state.login);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>();

  const onSubmit = handleSubmit(async (values) => {
    try {
      const session = await apiClient.post<AuthResponse>("/api/auth/register", values);
      login({
        userId: session.userId,
        email: session.email,
        roles: [session.role],
        accessToken: session.accessToken,
      });
      router.replace("/events");
    } catch {
      setError("root", { message: "가입할 수 없습니다. 이미 사용 중인 이메일인지 확인해주세요." });
    }
  });

  return (
    <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-6 px-6 py-16">
      <h1 className="text-2xl font-semibold">회원가입</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm font-medium">
          이름
          <input className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-transparent" {...register("name", { required: "이름을 입력하세요" })} />
          {errors.name && <span className="text-xs text-red-600">{errors.name.message}</span>}
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          이메일
          <input type="email" className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-transparent" {...register("email", { required: "이메일을 입력하세요" })} />
          {errors.email && <span className="text-xs text-red-600">{errors.email.message}</span>}
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          비밀번호
          <input type="password" className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-transparent" {...register("password", { required: "비밀번호를 입력하세요", minLength: { value: 8, message: "8자 이상 입력하세요" } })} />
          {errors.password && <span className="text-xs text-red-600">{errors.password.message}</span>}
        </label>
        {errors.root && <p className="text-sm text-red-600">{errors.root.message}</p>}
        <button type="submit" disabled={isSubmitting} className="rounded-full bg-blue-700 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50">
          가입하기
        </button>
      </form>
      <Link className="text-center text-sm font-medium text-blue-700" href="/login">로그인으로 돌아가기</Link>
    </div>
  );
}

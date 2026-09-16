"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { useSessionStore } from "@/store/useSessionStore";

interface LoginFormValues {
  email: string;
  password: string;
}

// SCR-01: 이메일/비밀번호 로그인.
// TODO: ticket-service에 인증 엔드포인트(JWT 발급)가 아직 없어 현재는 세션 스토어만 채운다.
export default function LoginPage() {
  const router = useRouter();
  const login = useSessionStore((state) => state.login);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>();

  const onSubmit = handleSubmit(async (values) => {
    login(crypto.randomUUID(), values.email);
    router.push("/events");
  });

  return (
    <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-6 px-6 py-16">
      <h1 className="text-2xl font-semibold">로그인</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="email" className="text-sm font-medium">
            이메일
          </label>
          <input
            id="email"
            type="email"
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-transparent"
            {...register("email", { required: "이메일을 입력하세요" })}
          />
          {errors.email && <p className="text-xs text-red-600">{errors.email.message}</p>}
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="password" className="text-sm font-medium">
            비밀번호
          </label>
          <input
            id="password"
            type="password"
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-transparent"
            {...register("password", { required: "비밀번호를 입력하세요" })}
          />
          {errors.password && <p className="text-xs text-red-600">{errors.password.message}</p>}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-2 rounded-full bg-blue-700 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
        >
          로그인
        </button>
      </form>
    </div>
  );
}

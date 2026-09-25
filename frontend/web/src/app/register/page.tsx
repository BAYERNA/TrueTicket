"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSessionStore } from "@/store/useSessionStore";
import { AuthResponseSchema } from "@/types/domain";

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
      const session = await apiClient.post("/api/auth/register", values, AuthResponseSchema);
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
        <div className="flex flex-col gap-1">
          <Label htmlFor="name">이름</Label>
          <Input id="name" {...register("name", { required: "이름을 입력하세요" })} />
          {errors.name && <p className="text-xs text-red-600">{errors.name.message}</p>}
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="email">이메일</Label>
          <Input id="email" type="email" {...register("email", { required: "이메일을 입력하세요" })} />
          {errors.email && <p className="text-xs text-red-600">{errors.email.message}</p>}
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="password">비밀번호</Label>
          <Input
            id="password"
            type="password"
            {...register("password", {
              required: "비밀번호를 입력하세요",
              minLength: { value: 8, message: "8자 이상 입력하세요" },
            })}
          />
          {errors.password && <p className="text-xs text-red-600">{errors.password.message}</p>}
        </div>
        {errors.root && <p className="text-sm text-red-600">{errors.root.message}</p>}
        <Button type="submit" disabled={isSubmitting} className="rounded-full">
          가입하기
        </Button>
      </form>
      <Link className="text-center text-sm font-medium text-blue-700" href="/login">
        로그인으로 돌아가기
      </Link>
    </div>
  );
}

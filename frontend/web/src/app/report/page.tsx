"use client";

import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { apiClient } from "@/lib/api-client";
import { useSessionStore } from "@/store/useSessionStore";

interface ReportFormValues {
  targetListingId: string;
  reportReason: string;
}

// SCR-11: 이용자가 의심되는 재판매 거래를 신고한다 (FR-013).
export default function ReportPage() {
  const userId = useSessionStore((state) => state.userId);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ReportFormValues>();

  const submitReport = useMutation({
    mutationFn: (values: ReportFormValues) =>
      apiClient.post("/api/reports", {
        targetListingId: values.targetListingId || null,
        reportReason: values.reportReason,
      }),
    onSuccess: () => reset(),
  });

  if (!userId) {
    return (
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col gap-4 px-6 py-12">
        <p className="text-sm text-zinc-500">신고하려면 먼저 로그인해주세요.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col gap-6 px-6 py-12">
      <h1 className="text-2xl font-semibold">이상거래 신고</h1>
      <form onSubmit={handleSubmit((values) => submitReport.mutate(values))} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="targetListingId" className="text-sm font-medium">
            게시물 ID (선택)
          </label>
          <input
            id="targetListingId"
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-transparent"
            {...register("targetListingId")}
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="reportReason" className="text-sm font-medium">
            신고 사유
          </label>
          <textarea
            id="reportReason"
            rows={4}
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-transparent"
            {...register("reportReason", { required: "신고 사유를 입력하세요" })}
          />
          {errors.reportReason && <p className="text-xs text-red-600">{errors.reportReason.message}</p>}
        </div>

        <button
          type="submit"
          disabled={submitReport.isPending}
          className="rounded-full bg-blue-700 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
        >
          신고 접수
        </button>

        {submitReport.isSuccess && <p className="text-sm text-green-700">신고가 접수되었습니다.</p>}
      </form>
    </div>
  );
}

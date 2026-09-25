"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface BotScoreLogEntry {
  scoreId: string;
  reservationSessionId: string;
  acquisitionFraudScore: number;
  isFlagged: boolean;
  evaluatedAt: string;
  modelVersion: string;
  reviewLabel: string | null;
}

// SCR-10: 예매 세션별 매크로/봇 탐지 스코어와 근거를 확인한다.
export default function BotLogsPage() {
  const queryClient = useQueryClient();
  const { data: scores, isPending } = useQuery({
    queryKey: ["bot-scores"],
    queryFn: () => apiClient.get<BotScoreLogEntry[]>("/api/bot-detection/scores"),
  });
  const feedback = useMutation({
    mutationFn: ({ scoreId, label }: { scoreId: string; label: string }) =>
      apiClient.post(`/api/bot-detection/scores/${scoreId}/feedback`, { label }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bot-scores"] }),
  });

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-6 py-12">
      <h1 className="text-2xl font-semibold">봇 탐지 로그</h1>

      {isPending && <p className="text-sm text-zinc-500">불러오는 중...</p>}

      <table className="w-full text-left text-sm">
        <thead className="text-zinc-500">
          <tr>
            <th className="py-2">예매 세션 ID</th>
            <th className="py-2">취득 부정성 스코어</th>
            <th className="py-2">플래그</th>
            <th className="py-2">평가 시각</th>
            <th className="py-2">모델/검수</th>
          </tr>
        </thead>
        <tbody>
          {scores?.map((score) => (
            <tr key={score.reservationSessionId} className="border-t border-zinc-100 dark:border-zinc-900">
              <td className="py-2 font-mono text-xs">{score.reservationSessionId}</td>
              <td className="py-2">{score.acquisitionFraudScore.toFixed(2)}</td>
              <td className="py-2">
                {score.isFlagged ? (
                  <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700 dark:bg-red-950 dark:text-red-300">
                    FLAGGED
                  </span>
                ) : (
                  <span className="text-zinc-400">-</span>
                )}
              </td>
              <td className="py-2 text-zinc-500">{new Date(score.evaluatedAt).toLocaleString("ko-KR")}</td>
              <td className="py-2">
                <p className="text-xs text-zinc-500">{score.modelVersion}</p>
                {score.reviewLabel ? (
                  <p className="text-xs font-medium">{score.reviewLabel}</p>
                ) : (
                  <div className="mt-1 flex gap-1">
                    <button
                      className="rounded border px-2 py-1 text-xs"
                      onClick={() => feedback.mutate({ scoreId: score.scoreId, label: "TRUE_POSITIVE" })}
                    >
                      정탐
                    </button>
                    <button
                      className="rounded border px-2 py-1 text-xs"
                      onClick={() => feedback.mutate({ scoreId: score.scoreId, label: "FALSE_POSITIVE" })}
                    >
                      오탐
                    </button>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

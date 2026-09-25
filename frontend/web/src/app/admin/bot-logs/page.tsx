"use client";

import {
  createColumnHelper,
  createSortedRowModel,
  rowSortingFeature,
  sortFn_basic,
  sortFn_datetime,
  tableFeatures,
  useTable,
} from "@tanstack/react-table";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface BotScoreLogEntry {
  scoreId: string;
  reservationSessionId: string;
  acquisitionFraudScore: number;
  isFlagged: boolean;
  evaluatedAt: string;
  modelVersion: string;
  reviewLabel: string | null;
}

const EMPTY_SCORES: BotScoreLogEntry[] = [];

const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { basic: sortFn_basic, datetime: sortFn_datetime },
});
const columnHelper = createColumnHelper<typeof features, BotScoreLogEntry>();

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

  const columns = useMemo(
    () =>
      columnHelper.columns([
        columnHelper.accessor("reservationSessionId", {
          header: "예매 세션 ID",
          enableSorting: false,
          cell: (info) => <span className="font-mono text-xs">{info.getValue()}</span>,
        }),
        columnHelper.accessor("acquisitionFraudScore", {
          header: "취득 부정성 스코어",
          sortFn: "basic",
          cell: (info) => info.getValue().toFixed(2),
        }),
        columnHelper.accessor("isFlagged", {
          header: "플래그",
          sortFn: "basic",
          cell: (info) =>
            info.getValue() ? (
              <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700 dark:bg-red-950 dark:text-red-300">
                FLAGGED
              </span>
            ) : (
              <span className="text-zinc-400">-</span>
            ),
        }),
        columnHelper.accessor("evaluatedAt", {
          header: "평가 시각",
          sortFn: "datetime",
          cell: (info) => new Date(info.getValue()).toLocaleString("ko-KR"),
        }),
        columnHelper.display({
          id: "review",
          header: "모델/검수",
          cell: ({ row }) => {
            const score = row.original;
            return (
              <div>
                <p className="text-xs text-zinc-500">{score.modelVersion}</p>
                {score.reviewLabel ? (
                  <p className="text-xs font-medium">{score.reviewLabel}</p>
                ) : (
                  <div className="mt-1 flex gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={() => feedback.mutate({ scoreId: score.scoreId, label: "TRUE_POSITIVE" })}
                    >
                      정탐
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={() => feedback.mutate({ scoreId: score.scoreId, label: "FALSE_POSITIVE" })}
                    >
                      오탐
                    </Button>
                  </div>
                )}
              </div>
            );
          },
        }),
      ]),
    [feedback],
  );

  const table = useTable({
    features,
    columns,
    data: scores ?? EMPTY_SCORES,
    initialState: { sorting: [{ id: "evaluatedAt", desc: true }] },
  });

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-6 py-12">
      <h1 className="text-2xl font-semibold">봇 탐지 로그</h1>

      {isPending && <p className="text-sm text-zinc-500">불러오는 중...</p>}

      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const canSort = header.column.getCanSort();
                const sortDirection = header.column.getIsSorted();
                return (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null : canSort ? (
                      <button
                        type="button"
                        className="hover:text-foreground flex items-center gap-1"
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        <table.FlexRender header={header} />
                        <span className="text-[10px]">
                          {sortDirection === "asc" ? "▲" : sortDirection === "desc" ? "▼" : ""}
                        </span>
                      </button>
                    ) : (
                      <table.FlexRender header={header} />
                    )}
                  </TableHead>
                );
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <TableRow key={row.id}>
              {row.getAllCells().map((cell) => (
                <TableCell key={cell.id}>
                  <table.FlexRender cell={cell} />
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

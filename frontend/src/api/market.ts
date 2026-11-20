export type Event = {
  id: string;
  name: string;
};

export type Channel = "가상 중고거래" | "가상 SNS";

export type PostDraft = {
  event_id: string;
  channel: Channel;
  author_handle: string;
  title: string;
  body: string;
  price: number | null;
};

export type MarketPost = PostDraft & {
  post_id: string;
  created_at: string;
};

export type Scan = {
  run_id: string;
  status: "ok" | "failed";
  post_count: number;
  post_ids: string[];
  error: string | null;
  http_status: number | null;
  extraction?:
    | { status: "api_key_required" }
    | { status: "completed" | "partial"; processed: number; ready: number; review: number; cached: number };
};

async function request<T>(path: string, payload?: object): Promise<T> {
  const response = await fetch(
    path,
    payload === undefined
      ? undefined
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
  );
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(typeof error?.detail === "string" ? error.detail : `요청 실패 (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const fetchEvents = () => request<Event[]>("/api/events");
export const fetchPosts = () => request<MarketPost[]>("/api/market/posts");
export const addPost = (draft: PostDraft) => request<MarketPost>("/api/market/posts", draft);
export async function scanPosts(eventId: string): Promise<Scan> {
  const started = await request<{run_id: string}>("/api/agent/runs", { event_id: eventId || null, mode: "local" });
  for (let attempt = 0; attempt < 120; attempt++) {
    const run = await request<{status: string; steps: {step: string; output_summary: unknown}[]}>(`/api/agent/runs/${started.run_id}`);
    if (run.status !== "running") {
      const collected = run.steps.find(step => step.step === "collect")?.output_summary as Omit<Scan, "run_id"> | undefined;
      if (!collected) throw new Error("수집 실행 기록을 확인할 수 없습니다.");
      if (run.status === "failed" && collected.status === "ok") {
        throw new Error("게시글 수집 후 분석이 중단되었습니다. 대시보드의 실행 기록을 확인해 주세요.");
      }
      const extraction = run.steps.find(step => step.step === "extract")?.output_summary as Scan["extraction"];
      return { ...collected, run_id: started.run_id, extraction };
    }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error("분석을 계속 실행 중입니다. 대시보드에서 실행 기록을 확인해 주세요.");
}
export const resetMarket = () => request<{status: string; counts: Record<string, number>}>("/api/demo/reset", {});

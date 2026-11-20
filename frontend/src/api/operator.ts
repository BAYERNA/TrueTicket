export type Config = { gemini_configured: boolean; default_mode: "local" | "gemini"; extraction_model: string; embedding_model: string };
export type Risk = "높음" | "중간" | "낮음" | "확인 불가";
export type CaseSummary = {
  case_id: string; post_id: string; event_id: string; title: string; status: string; risk_level: Risk;
  seats: string[] | null; price_per_ticket_krw: number | null; matched_booking_ids: string[]; rule_hits: string[]; provider: string;
};
export type Overview = { case_count: number; statuses: Record<string, number>; risks: Record<string, number>; offered_count: number; false_positive_count: number; latest_run_id: string | null; api_requests: Record<string, number>; daily_request_limit: number };
export type Run = { run_id: string; status: string; steps: { step: string; tool: string; latency: number; output_summary: Record<string, unknown> }[] };
export type Booking = { booking_id: string; account_id: string; nickname: string; seat: string; grade: string; price_paid: number; booked_at: string; current_status: string; bot: { score: number; evidence: { click_interval_count: number; click_interval_cv: number | null; automation_signature_count: number } } };
export type ActionType = "request_explanation" | "close_normal" | "cancel_redistribute" | "draft_report";
export type Allocation = { fan_id: string; seat: string; price: number; message: string };
export type CaseDetail = {
  case_id: string; status: string;
  post: { post_id: string; event_id: string; title: string; body: string; author_handle: string; channel: string };
  extraction: { provider?: string; source: string; reason: string | null; fields: { seats: string[] | null; quantity: number | null; price_per_ticket_krw: number | null; trade_method: string | null; confidence: Record<string, number>; evidence: Record<string, string[]> } | null };
  match: { matched_booking_ids: string[]; bookings: Booking[]; failure_reason: string | null };
  risk: { risk_level: Risk; rule_hits: string[]; evidence: Record<string, unknown>; above_cost_seat_count: number };
  cluster: { method: string; post_ids: string[]; evidence: { reason: string; similarity: number | null }[] };
  related_posts: { post_id: string; case_id: string; title: string; author_handle: string; channel: string }[];
  slang: { term: string; meaning: string }[];
  explanation: { text: string; generated_by_ai: boolean; source: string };
  actions: { type: string; at: string; actor: string; text?: string; deadline?: string; allocations?: Allocation[]; false_positive?: boolean }[];
};
export type Approval = { approval_id: string; type: ActionType; document: { text: string; generated_by_ai: boolean }; status: string };

export async function api<T>(path: string, payload?: unknown): Promise<T> {
  const response = await fetch(path, payload === undefined ? undefined : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : `요청 실패 (${response.status})`);
  return data as T;
}

export const won = (value: number | null | undefined) => value == null ? "확인 불가" : `${value.toLocaleString("ko-KR")}원`;
export const steps: Record<string, string> = { collect: "HTTP 수집", mask: "개인정보 마스킹", extract: "정보 추출", match: "예매 연결", bot_score: "봇 점수", cluster: "판매자 후보 묶기", assess: "위험 판단", failed: "실행 오류" };
export const actionLabels: Record<string, string> = { request_explanation: "소명 요청", close_normal: "정상 처리", cancel_redistribute: "취소·정가 재배분", draft_report: "신고서 초안", deadline_elapsed: "소명 기한 경과", explanation_received: "소명 접수", approval_requested: "승인 요청" };
export const ruleLabels: Record<string, string> = { R1: "구입가 초과", R2: "2장 이상 초과 판매", R3: "정가 2배 이상", R4: "부정구매 의심", R5: "사기 신호" };
export const failureLabels: Record<string, string> = {
  missing_seats: "좌석 정보 없음", missing_price: "가격 정보 없음", missing_quantity: "유효한 판매 수량 없음",
  seat_not_found: "없는 좌석", cancelled_booking: "취소된 예매", quantity_mismatch: "수량·좌석 수 불일치",
  unknown_event: "공연·회차 확인 불가", low_confidence: "추출 신뢰도 부족",
};

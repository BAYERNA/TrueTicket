import { useEffect, useState } from "react";
import { api, steps, won } from "../api/operator";
import type { CaseSummary, Config, Overview, Run } from "../api/operator";
import type { Event } from "../api/market";
import { Header } from "../components/Header";

const riskClass: Record<string, string> = { "높음": "high", "중간": "medium", "낮음": "low", "확인 불가": "unknown" };
const runLabels: Record<string, string> = {running: "분석 중", failed: "실행 오류", partial: "일부 완료", completed: "실행 종료"};
type Evaluation = { status: string; validation_scope?: string; ai_acceptance_verified?: boolean; error?: string; metrics?: Record<string, number> };

export function RiskBadge({ risk }: { risk: string }) {
  return <span className={`risk-badge ${riskClass[risk] || "unknown"}`}>{risk}</span>;
}

export function Dashboard() {
  const [config, setConfig] = useState<Config | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [eventId, setEventId] = useState("");
  const [mode, setMode] = useState<"local" | "gemini">("local");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [risk, setRisk] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);

  async function refresh() {
    const [stats, items] = await Promise.all([api<Overview>("/api/overview"), api<CaseSummary[]>("/api/cases")]);
    setOverview(stats); setCases(items);
    return stats;
  }

  useEffect(() => {
    Promise.all([api<Config>("/api/config"), api<Event[]>("/api/events"), refresh()]).then(([settings, list, stats]) => {
      setConfig(settings); setMode(settings.default_mode); setEvents(list);
      if (stats.latest_run_id) api<Run>(`/api/agent/runs/${stats.latest_run_id}`).then(setRun).catch(() => {});
    }).catch(e => setError(e.message)).finally(() => setLoading(false));
    api<Evaluation>("/api/eval").then(setEvaluation).catch(() => {});
  }, []);

  useEffect(() => {
    if (!run || run.status !== "running") return;
    let disposed = false;
    const timer = window.setTimeout(async () => {
      try {
        const next = await api<Run>(`/api/agent/runs/${run.run_id}`);
        if (disposed) return;
        setRun(next);
        if (next.status !== "running") { setBusy(false); await refresh(); }
      } catch (e) {
        if (!disposed) { setError((e as Error).message); setBusy(false); }
      }
    }, 1000);
    return () => { disposed = true; clearTimeout(timer); };
  }, [run]);

  useEffect(() => {
    if (evaluation?.status !== "running") return;
    const timer = setTimeout(() => { api<Evaluation>("/api/eval").then(setEvaluation).catch(e => setError(e.message)); }, 1200);
    return () => clearTimeout(timer);
  }, [evaluation]);

  async function evaluate() {
    setError("");
    try { setEvaluation(await api<Evaluation>("/api/eval", { mode })); }
    catch (e) { setError((e as Error).message); }
  }

  async function scan() {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await api<{ run_id: string }>("/api/agent/runs", { event_id: eventId || null, mode });
      setRun({ run_id: result.run_id, status: "running", steps: [] });
    } catch (e) { setError((e as Error).message); setBusy(false); }
  }

  async function reset() {
    setError(""); setBusy(true);
    try { await api("/api/demo/reset", {}); setRun(null); await refresh(); setNotice("가상 데이터와 케이스를 초기 상태로 복원했습니다."); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  const visible = cases.filter(c => (!risk || c.risk_level === risk) && (!eventId || c.event_id === eventId)
    && `${c.post_id} ${c.title} ${c.matched_booking_ids.join(" ")}`.toLowerCase().includes(search.trim().toLowerCase()));
  const queue = window.location.pathname === "/cases";
  return <><Header /><main className="shell operator">
    <section className="hero"><div><p className="eyebrow">공연 운영자</p><h1>{queue ? "의심 큐" : "암표 대응 대시보드"}</h1>
      <p>게시글과 예매 기록을 확인하고, 소명부터 정가 재배분까지 처리하세요.</p></div>
      <div className="actions"><button onClick={reset} disabled={loading}>{busy ? "감시 중단·초기화" : "데모 초기화"}</button>
        <button className="primary" onClick={scan} disabled={busy || loading || evaluation?.status === "running"}>{busy ? "분석 중…" : "에이전트 감시 시작"}</button></div></section>
    {error && <p className="message error" role="alert">{error}</p>}
    {notice && <p className="message" role="status">{notice}</p>}
    <section className="scan-settings panel">
      <label>공연<select value={eventId} onChange={e => setEventId(e.target.value)} disabled={busy}>
        <option value="">전체 공연</option>{events.map(e => <option value={e.id} key={e.id}>{e.name}</option>)}</select></label>
      <label>분석 방식<select value={mode} onChange={e => setMode(e.target.value as "local" | "gemini")} disabled={busy}>
        <option value="local">규칙 데모 · API 호출 0건</option><option value="gemini" disabled={!config?.gemini_configured}>Gemini 분석{config?.gemini_configured ? "" : " · 서버 키 설정 필요"}</option></select></label>
      <p className="mode-note">{mode === "local" ? "규칙으로 전체 처리 흐름을 시연합니다. AI 모델의 정확도는 별도 실측이 필요합니다." : "마스킹한 가상 게시글로 Gemini를 호출합니다. 무료 등급과 호출 한도는 API 프로젝트 설정을 따릅니다."}</p>
    </section>
    <section className="stats" aria-label="전체 처리 현황">
      {[['전체 케이스', overview?.case_count || 0], ['높은 위험', overview?.risks['높음'] || 0], ['소명 대기', overview?.statuses['소명 대기'] || 0], ['정가 구매 안내', overview?.offered_count || 0], ['오탐으로 정상 종료', overview?.false_positive_count || 0]].map(([label, value]) =>
        <div className="stat panel" key={label}><span>{label}</span><strong>{value}</strong><small>건</small></div>)}
    </section>
    {run && <section className="panel execution" aria-live="polite"><div className="panel-heading"><h2>실행 기록</h2><span>{runLabels[run.status] || run.status}</span></div>
      <ol className="step-list">{run.steps.map(s => <li key={s.step}><strong>{steps[s.step] || s.step}</strong><span>{s.latency.toLocaleString()} ms</span>
        {s.output_summary.error != null && <span className="error-text">{s.output_summary.error === "daily_request_limit" || s.output_summary.error === "gemini_http_429" ? "호출 한도에 도달했습니다. 한도가 회복되면 다시 실행하세요." : String(s.output_summary.error)}</span>}</li>)}
        {run.status === "running" && <li>다음 단계를 처리하고 있습니다.</li>}</ol></section>}
    <section className="panel case-list"><div className="panel-heading"><h2>케이스</h2><span>{visible.length}건</span></div>
      <div className="case-filters"><label>위험 등급<select value={risk} onChange={e => setRisk(e.target.value)}><option value="">전체 등급</option>{Object.keys(riskClass).map(r => <option key={r}>{r}</option>)}</select></label>
        <label>검색<input value={search} onChange={e => setSearch(e.target.value)} placeholder="게시글·예매 ID 또는 제목" /></label></div>
      <div className="table-scroll"><table><thead><tr><th>게시글</th><th>위험</th><th>좌석</th><th>장당 판매가</th><th>연결 예매</th><th>처리 상태</th></tr></thead><tbody>
        {visible.map(c => <tr key={c.case_id}><td><a className="case-link" href={`/cases/${c.case_id}`}>{c.title}</a><code>{c.post_id}</code></td>
          <td><RiskBadge risk={c.risk_level} /></td><td>{c.seats?.join(", ") || "확인 불가"}</td><td>{won(c.price_per_ticket_krw)}</td>
          <td>{c.matched_booking_ids.length}건</td><td>{c.status}</td></tr>)}
      </tbody></table></div>
      {!visible.length && <div className="empty-state"><h3>{loading ? "불러오는 중입니다" : cases.length ? "조건에 맞는 케이스가 없습니다" : "감시를 시작해 예매 기록을 연결하세요"}</h3>
        <p>가상 마켓의 게시글을 수집하고 가격·좌석·예매 근거를 확인할 수 있어요.</p><a href="/market">가상 리셀 마켓 열기</a></div>}
    </section>
    <section className="panel evaluation-panel"><div className="panel-heading"><h2>평가셋 검증</h2><button onClick={evaluate} disabled={busy || loading || evaluation?.status === "running"}>{evaluation?.status === "running" ? "평가 중…" : `${mode === "local" ? "규칙" : "Gemini"} 평가 실행`}</button></div>
      <div className="panel-content"><p className="muted">{evaluation?.validation_scope === "local_rules" ? "규칙 데모 실측 · AI 모델 평가는 대기 중입니다." : evaluation?.validation_scope === "gemini_live" ? "Gemini 실측 결과" : "가상 게시글 80건을 정답과 대조합니다."}</p>
        {evaluation?.metrics && <div className="metric-row">{[["추출 일치율", "field_accuracy"], ["예매 연결", "booking_match_accuracy"], ["판매자 군집", "seller_cluster_accuracy"], ["부정판매 탐지", "resale_detection_rate"], ["정가 양도 오탐", "normal_false_positive_rate"]].map(([label, key]) => <span key={key}>{label}<strong>{((evaluation.metrics?.[key] || 0) * 100).toFixed(1)}%</strong></span>)}</div>}
        {evaluation?.error && <p className="error-text" role="alert">{evaluation.error}</p>}
      </div></section>
  </main></>;
}

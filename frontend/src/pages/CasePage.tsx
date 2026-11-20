import { useEffect, useRef, useState } from "react";
import { actionLabels, api, failureLabels, ruleLabels, won } from "../api/operator";
import type { ActionType, Approval, CaseDetail } from "../api/operator";
import { Header } from "../components/Header";
import { RiskBadge } from "./Dashboard";

function EvidenceText({ text, quotes }: { text: string; quotes: string[] }) {
  const meaningful = [...new Set(quotes)].filter(Boolean).sort((a, b) => b.length - a.length);
  if (!meaningful.length) return <>{text}</>;
  const expression = new RegExp(`(${meaningful.map(q => q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "g");
  return <>{text.split(expression).map((part, index) => meaningful.includes(part) ? <mark key={index}>{part}</mark> : part)}</>;
}

export function CasePage({ caseId }: { caseId: string }) {
  const [item, setItem] = useState<CaseDetail | null>(null);
  const [approval, setApproval] = useState<Approval | null>(null);
  const [text, setText] = useState("");
  const [approved, setApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const dialog = useRef<HTMLElement>(null);
  useEffect(() => { api<CaseDetail>(`/api/cases/${caseId}`).then(setItem).catch(e => setError(e.message)); }, [caseId]);
  useEffect(() => {
    if (!approval) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.current?.querySelector<HTMLTextAreaElement>("textarea")?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") { setApproval(null); return; }
      if (event.key !== "Tab") return;
      const items = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), textarea') || []);
      if (event.shiftKey && document.activeElement === items[0]) { event.preventDefault(); items.at(-1)?.focus(); }
      else if (!event.shiftKey && document.activeElement === items.at(-1)) { event.preventDefault(); items[0]?.focus(); }
    }
    document.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = previousOverflow; document.removeEventListener("keydown", onKey); previousFocus?.focus(); };
  }, [approval]);

  async function preview(type: ActionType) {
    setBusy(true); setError(""); setNotice("");
    try { const value = await api<Approval>(`/api/cases/${caseId}/approvals`, { type }); setApproval(value); setText(value.document.text); setApproved(false); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function execute() {
    if (!approval || !approved) return;
    setBusy(true); setError("");
    try {
      const value = await api<{ case: CaseDetail }>(`/api/cases/${caseId}/actions`, { type: approval.type, approval_id: approval.approval_id, approved, edited_text: text });
      setItem(value.case); setNotice(`${actionLabels[approval.type]} 처리를 데모에 반영했습니다.`); setApproval(null);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function simulate(type: "deadline_elapsed" | "explanation_received") {
    setBusy(true); setError("");
    try { setItem(await api<CaseDetail>(`/api/cases/${caseId}/simulate`, { type })); setNotice(`${actionLabels[type]}를 반영했습니다.`); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  const fields = item?.extraction.fields;
  const quotes = Object.values(fields?.evidence || {}).flat();
  const hits = item?.risk.rule_hits || [];
  const expired = item?.actions.some(a => a.type === "deadline_elapsed");
  const replied = item?.actions.some(a => a.type === "explanation_received");
  const allocations = item?.actions.flatMap(a => a.allocations || []) || [];
  const awaiting = item?.status === "소명 대기";
  return <><Header /><main className="shell operator case-detail">
    <a className="back-link" href="/cases">의심 큐로 돌아가기</a>
    {error && <p className="message error" role="alert">{error}</p>}
    {notice && <p className="message" role="status">{notice}</p>}
    {!item ? <p className="empty">케이스를 불러오는 중입니다.</p> : <>
      <section className="hero"><div><div className="case-kicker"><code>{item.case_id}</code><RiskBadge risk={item.risk.risk_level} /><span>{item.status}</span></div>
        <h1><EvidenceText text={item.post.title} quotes={quotes} /></h1><p>{item.extraction.provider === "gemini" ? "Gemini 분석" : "규칙 데모"} · 가상 게시글과 내부 예매 기록</p></div></section>
      <div className="evidence-grid">
        <section className="panel evidence-panel"><div className="panel-heading"><h2>외부 게시글</h2><span>{item.post.channel}</span></div>
          <div className="panel-content"><p className="muted">{item.post.author_handle} · {item.post.post_id}</p>
            <p className="original-text"><EvidenceText text={item.post.body} quotes={quotes} /></p>
            <p className="muted">추출 근거를 제목과 본문에 표시했습니다. 개인정보는 마스킹되어 있어요.</p>
            <dl className="field-grid"><div><dt>장당 판매가</dt><dd>{won(fields?.price_per_ticket_krw)}</dd><small>신뢰도 {Math.round((fields?.confidence.price_per_ticket_krw || 0) * 100)}%</small></div>
              <div><dt>수량</dt><dd>{fields?.quantity == null ? "확인 불가" : `${fields.quantity}장`}</dd></div>
              <div><dt>좌석</dt><dd>{fields?.seats?.join(", ") || "확인 불가"}</dd><small>신뢰도 {Math.round((fields?.confidence.seats || 0) * 100)}%</small></div>
              <div><dt>거래 방식</dt><dd>{fields?.trade_method || "확인 불가"}</dd></div></dl>
            {item.slang.length > 0 && <div className="slang-list">{item.slang.map(s => <p key={s.term}><strong>{s.term}</strong> · {s.meaning}</p>)}</div>}
          </div></section>
        <section className="panel evidence-panel"><div className="panel-heading"><h2>내부 예매 근거</h2><span>{item.match.bookings.length}건 연결</span></div>
          <div className="panel-content">{item.match.failure_reason && <p className="message">{failureLabels[item.match.failure_reason] || item.match.failure_reason}</p>}
            {item.match.bookings.map(b => <article className="booking-card" key={b.booking_id}><div className="booking-heading"><strong>{b.seat}</strong><span>{b.current_status === "cancelled" ? "취소됨" : "예매 확정"}</span></div><code>{b.booking_id}</code>
              <dl><div><dt>예매 계정</dt><dd>{b.account_id} · {b.nickname}</dd></div><div><dt>구입가</dt><dd>{won(b.price_paid)} · 수수료 포함</dd></div>
                <div><dt>예매 시각</dt><dd>{new Date(b.booked_at).toLocaleString("ko-KR")}</dd></div></dl>
              <div className="bot-evidence"><strong>봇 점수 {b.bot.score.toFixed(3)}</strong><p>클릭 간격 {b.bot.evidence.click_interval_count}개 · 변동계수 {b.bot.evidence.click_interval_cv?.toFixed(4) ?? "계산 불가"} · 자동화 흔적 {b.bot.evidence.automation_signature_count}건</p></div>
            </article>)}
            {!item.match.bookings.length && <p className="muted">연결할 수 있는 유효한 예매가 확인되지 않았습니다.</p>}
          </div></section>
      </div>
      <div className="evidence-grid secondary-grid"><section className="panel evidence-panel"><div className="panel-heading"><h2>위험 판단 근거</h2><RiskBadge risk={item.risk.risk_level} /></div>
        <div className="panel-content"><ul className="rule-list">{Object.entries(ruleLabels).map(([key, label]) => <li key={key} className={hits.includes(key) ? "rule-hit" : "rule-clear"}>
          <strong>{key}</strong><span>{label}</span><span>{item.risk.risk_level === "확인 불가" ? "미평가" : hits.includes(key) ? "신호 확인" : "미충족"}</span></li>)}</ul>
          <div className="explanation"><span className="source-label">{item.explanation.generated_by_ai ? "AI가 생성한 답변" : "규칙으로 구성한 설명"}</span><p>{item.explanation.text}</p></div>
          <p className="muted">기획서의 규칙을 적용한 운영 검토용 의심 등급입니다.</p>
        </div></section>
        <section className="panel evidence-panel"><div className="panel-heading"><h2>같은 판매자 후보</h2><span>{item.related_posts.length}건</span></div><div className="panel-content">
          <p className="muted">{item.cluster.method === "local_rules" ? "작성자·거래 문구 규칙" : "임베딩 유사도와 거래 문구 근거"} · 중복 제외 초과 판매 좌석 {item.risk.above_cost_seat_count}개</p>
          <ul className="related-list">{item.related_posts.map(p => <li key={p.post_id}><a href={`/cases/${p.case_id}`}>{p.post_id} · {p.title}</a><span>{p.author_handle} · {p.channel}</span></li>)}</ul>
        </div></section></div>
      <section className="panel action-panel"><div className="panel-heading"><h2>운영자 조치</h2><span>승인 후 데모 상태에 반영</span></div><div className="panel-content">
        <div className="actions wrap"><button onClick={() => preview("request_explanation")} disabled={busy || item.status !== "신규" || !["높음", "중간"].includes(item.risk.risk_level)}>소명 요청</button>
          <button onClick={() => preview("close_normal")} disabled={busy || !["신규", "소명 대기"].includes(item.status)}>정상 처리</button>
          <button className="danger" onClick={() => preview("cancel_redistribute")} disabled={busy || !awaiting || !expired || replied || item.risk.risk_level !== "높음"}>예매 취소·정가 재배분</button>
          <button onClick={() => preview("draft_report")} disabled={busy}>신고서 초안</button></div>
        {awaiting && <div className="simulation-tools"><span>소명 데모</span><button onClick={() => simulate("deadline_elapsed")} disabled={busy || expired}>소명 기한 경과</button>
          <button onClick={() => simulate("explanation_received")} disabled={busy || replied}>소명 도착</button></div>}
        {allocations.length > 0 && <div className="allocations"><h3>정가 구매 안내</h3>{allocations.map(a => <p key={a.seat}><strong>{a.fan_id}</strong> · {a.message}</p>)}</div>}
      </div></section>
      <section className="panel history"><div className="panel-heading"><h2>처리 이력</h2><a href={`/api/cases/${caseId}/report`}>현재 신고서 내려받기</a></div>
        <ol>{item.actions.filter(a => a.type !== "approval_requested").map((a, index) => <li key={index}><strong>{actionLabels[a.type] || a.type}</strong><span>{new Date(a.at).toLocaleString("ko-KR")} · {a.actor}</span>
          {a.text && <p>{a.text}</p>}{a.false_positive && <p>오탐 기록 저장됨</p>}</li>)}</ol>
        {!item.actions.some(a => a.type !== "approval_requested") && <p className="empty">아직 실행한 조치가 없습니다.</p>}
      </section>
    </>}
    {approval && <div className="modal-backdrop"><section ref={dialog} className="approval-dialog" role="dialog" aria-modal="true" aria-labelledby="approval-title"><h2 id="approval-title">{actionLabels[approval.type]} 승인</h2>
      <p>{approval.document.generated_by_ai ? "AI가 생성한 답변을 포함한 초안" : "규칙·템플릿으로 만든 초안"} · 내용을 확인하고 수정할 수 있어요.</p>
      <label className="sr-only" htmlFor="document-text">조치 문서 내용</label><textarea id="document-text" value={text} onChange={e => setText(e.target.value)} rows={14} maxLength={16000} />
      <label className="approval-check"><input type="checkbox" checked={approved} onChange={e => setApproved(e.target.checked)} />내용과 근거를 확인했고, 데모 조치를 승인합니다.</label>
      <div className="actions"><button onClick={() => setApproval(null)} disabled={busy}>닫기</button><button className="primary" onClick={execute} disabled={busy || !approved}>승인하고 실행</button></div>
    </section></div>}
  </main></>;
}

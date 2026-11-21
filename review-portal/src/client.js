"use strict";
const app = document.querySelector("#app"),
  notice = document.querySelector("#notice");
const url = new URL(location.href),
  given = url.searchParams.get("w");
const operatorEntry = url.searchParams.get("view") === "operator";
let previous = null;
try {
  previous = localStorage.getItem("tg:last-workspace");
} catch {}
const state = {
  data: null,
  w: given || (operatorEntry ? previous : null),
  role: operatorEntry ? "operator" : "audience",
  item:
    given || url.searchParams.get("case") === "hanbit" ? "hanbit" : "SP-FEST",
  analyzed: false,
  inbox: null,
};
const encode = (x) =>
  String(x ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const won = (n) => n.toLocaleString("ko-KR") + "원";
const button = (act, title, primary = false) =>
  '<button data-action="' +
  act +
  '"' +
  (primary ? ' class="primary"' : "") +
  ">" +
  title +
  "</button>";
const phase = {
  open: "검토 대기",
  awaiting: "소명 대기",
  appealed: "소명 접수 · 재배분 보류",
  offered: "정가 구매 안내 발행",
};
const levels = {
  CAUTION: "주의",
  REVIEW: "추가 확인",
  INSUFFICIENT: "자료 부족",
};
const sections = {
  facts: "확인된 사실",
  signals: "의심 정황",
  unknowns: "확인 불가",
  actions: "권고 행동",
};
async function api(path, data) {
  const opts =
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        };
  const response = await fetch(path, opts);
  const v = await response.json();
  if (!response.ok) {
    const e = new Error(v.error || "요청을 처리하지 못했습니다.");
    e.status = response.status;
    throw e;
  }
  return v;
}
const endpoint = (verb) => "/api/workspaces/" + state.w + "/" + verb;
const guestURL = () => {
  const u = new URL("/", location.origin);
  u.searchParams.set("w", state.w);
  return u.href;
};
const key = (s) => "tg:" + state.w + ":" + s;
const collection = (items) =>
  "<ul>" + items.map((x) => "<li>" + encode(x) + "</li>").join("") + "</ul>";
function viewTabs() {
  document
    .querySelector("#audience")
    .classList.toggle("active", state.role === "audience");
  document
    .querySelector("#operator")
    .classList.toggle("active", state.role === "operator");
}
function intro(title, desc, side) {
  return (
    '<section class="intro"><div><h1>' +
    title +
    "</h1><p>" +
    desc +
    '</p></div><div class="ticket" aria-hidden="true">TicketGuard<small>' +
    side +
    "</small></div></section>"
  );
}
function choices() {
  const rows = [
    ...state.data.samples.map((s) => [s.id, s.label, s.date]),
    ["hanbit", "콘서트 · 운영자 검토", "한빛 겨울 콘서트"],
  ];
  return (
    '<section class="panel"><h2>시연 사례</h2><div class="choices">' +
    rows
      .map(
        ([id, title, sub]) =>
          '<button class="choice" data-case="' +
          id +
          '" aria-pressed="' +
          (state.item === id) +
          '">' +
          encode(title) +
          "<small>" +
          encode(sub) +
          "</small></button>",
      )
      .join("") +
    '</div><p class="muted">모든 공연·좌석·가격은 시연용 가상 자료입니다.</p></section>'
  );
}
function result(s) {
  const r = s.report;
  return (
    '<section class="panel"><span class="pill ' +
    (r.level === "CAUTION" ? "warn" : "") +
    '">' +
    levels[r.level] +
    " · 프리셋</span><h2>거래 전 점검 결과</h2><p>장당 기준가 " +
    won(r.list_price_krw) +
    " · 제시액 " +
    won(r.asking_price_krw) +
    '</p><div class="grid">' +
    Object.entries(sections)
      .map(
        ([k, v]) =>
          '<div class="card"><h3>' +
          v +
          "</h3>" +
          collection(r[k].length ? r[k] : ["표시할 항목이 없습니다."]) +
          "</div>",
      )
      .join("") +
    '</div><p class="muted sub">' +
    encode(r.benchmark_source) +
    '</p><div class="actions"><a class="btn primary" download href="/reports/' +
    s.id +
    '.txt">점검 결과 TXT 저장</a><a class="btn" href="https://www.culture.go.kr/singo/" target="_blank" rel="noopener noreferrer">공식 신고센터</a></div></section>'
  );
}
function standard() {
  const s = state.data.samples.find((s) => s.id === state.item);
  return (
    '<section class="panel"><div class="caseMeta">' +
    s.date +
    " · 가상 판매글</div><h2>" +
    encode(s.name) +
    '</h2><p class="quote">' +
    encode(s.text) +
    "</p>" +
    button("analyze", "가격과 입장 조건 점검", true) +
    "</section>" +
    (state.analyzed ? result(s) : "")
  );
}
function recentReceipt() {
  try {
    return JSON.parse(sessionStorage.getItem(key("receipt")) || "null");
  } catch {
    return null;
  }
}
function hanbit() {
  const h = state.data.hanbit,
    receipt = recentReceipt();
  return (
    '<section class="panel"><div class="caseMeta">' +
    h.date +
    " · " +
    h.session +
    "</div><h2>" +
    h.name +
    '</h2><p class="quote">' +
    encode(h.text) +
    '</p><div class="grid"><div class="card"><h3>장당 기준가</h3><p class="price">' +
    won(h.listed) +
    '</p></div><div class="card"><h3>장당 제시액</h3><p class="price">' +
    won(h.asking) +
    '</p></div></div><p class="sub">가격표보다 장당 ' +
    won(h.asking - h.listed) +
    ' 높습니다. 판매자의 실제 구입가는 관객 화면에서 확인할 수 없습니다.</p></section><section class="panel"><h2>운영자에게 검토 요청</h2><p class="muted">수신처는 ' +
    encode(h.organizer) +
    "입니다. 행사·회차, 원본 글 번호, 좌석 후보, 제시액과 선택한 문구를 전달합니다. 실제 신고·예매 처리와는 별개의 시연입니다.</p>" +
    (state.w
      ? '<div class="sub"><h3>보낼 근거 문구</h3>' +
        h.evidence
          .map(
            (v, i) =>
              '<label class="formcheck"><input type="checkbox" name="evidence" value="' +
              i +
              '" checked>' +
              encode(v) +
              "</label>",
          )
          .join("") +
        '<label class="formcheck"><input id="consent" type="checkbox">위 항목을 이 시연 공간의 운영자에게 보내는 데 동의합니다.</label>' +
        button("submit", "선택한 근거로 접수", true) +
        (receipt
          ? '<p class="receipt"><b>최근 접수번호</b><br>' +
            encode(receipt) +
            "</p>"
          : "") +
        "</div>"
      : '<div class="actions">' +
        button("create", "개인 시연 공간 만들기", true) +
        '</div><p class="muted">이 브라우저에서 관객과 가상 운영자를 모두 체험하거나 관객 링크를 공유할 수 있습니다.</p>') +
    "</section>"
  );
}
function audience() {
  state.role = "audience";
  viewTabs();
  app.innerHTML =
    intro(
      "티켓 거래 전 점검",
      "가상 판매글의 가격과 입장 조건을 비교하고, 필요한 근거를 운영자에게 보내세요.",
      "관객용 점검표",
    ) +
    '<div class="layout">' +
    choices() +
    '<div class="column">' +
    (state.item === "hanbit" ? hanbit() : standard()) +
    "</div></div>";
}
function opPanel() {
  const r = state.inbox;
  if (!r) return "";
  const deadline = r.deadline
    ? new Date(r.deadline).toLocaleString("ko-KR", {
        timeZone: "Asia/Seoul",
        hour12: false,
      })
    : "";
  const rows = r.receipts
    .map(
      (x) =>
        '<div class="row"><b>' +
        encode(x.receipt) +
        "</b><br>" +
        encode(x.evidence.join(" · ")) +
        "</div>",
    )
    .join("");
  const actions =
    r.state === "open" && r.receipts.length
      ? button("explain", "소명 요청", true)
      : r.state === "awaiting"
        ? button("reply", "소명 도착 재현") +
          " " +
          button("elapse", "시연 기한 경과") +
          '<label class="formcheck"><input type="checkbox" id="approval">고위험 근거와 소명 기한을 확인하고 두 좌석의 모의 취소·재배분을 승인합니다.</label>' +
          button("approve", "승인 후 정가 구매 안내", true)
        : "";
  return (
    '<div class="layout"><div class="column"><section class="panel"><h2>관객 초대 링크</h2><p class="muted">이 링크로 들어오면 같은 공연에 검토를 요청할 수 있습니다.</p><input class="linkfield" id="invite" aria-label="관객 초대 링크" readonly value="' +
    encode(guestURL()) +
    '"><div class="actions">' +
    button("copy", "링크 복사") +
    button("guest", "관객으로 보기") +
    '</div></section><section class="panel"><h2>관객 접수 ' +
    r.receipts.length +
    "건</h2>" +
    (rows || '<p class="muted">아직 접수된 요청이 없습니다.</p>') +
    '<div class="actions">' +
    button("refresh", "접수함 새로고침") +
    '</div></section></div><div class="column"><section class="panel"><span class="pill">' +
    phase[r.state] +
    "</span><h2>한빛 겨울 콘서트 · " +
    encode(r.session) +
    '</h2><p class="muted">운영자 감시 사례 ' +
    encode(r.caseId) +
    " · " +
    encode(r.source) +
    '</p><div class="grid">' +
    r.bookings
      .map(
        (b) =>
          '<div class="card"><h3>' +
          encode(b.seat) +
          "</h3><p>" +
          encode(b.booking) +
          "</p><p>구입가 " +
          won(b.paid) +
          "<br>구입가 대비 +" +
          won(b.difference) +
          "<br>봇 점수 " +
          b.score.toFixed(3) +
          "</p></div>",
      )
      .join("") +
    '</div><p class="sub">모의 위험 등급 ' +
    (r.high ? "높음" : "검토") +
    ' · 정가 초과 좌석 수와 예매 행동 지표를 함께 확인합니다.</p></section><section class="panel"><h2>소명 및 정가 재배분</h2><p>' +
    (r.state === "appealed"
      ? "소명이 접수되어 자동 취소·재배분을 보류했습니다."
      : r.state === "offered"
        ? "가상 대기자에게 구매 기회를 안내했습니다."
        : r.state === "open"
          ? "관객 접수 후 운영자가 소명을 요청할 수 있습니다."
          : "소명 기한 " + encode(deadline) + " (한국시간)") +
    '</p><div class="sub">' +
    actions +
    "</div>" +
    r.offers
      .map(
        (o) =>
          '<div class="row">' +
          encode(o.seat) +
          " · " +
          encode(o.fan) +
          " · <b>" +
          won(o.price) +
          "</b> 구매 안내</div>",
      )
      .join("") +
    "</section></div></div>"
  );
}
async function operator() {
  state.role = "operator";
  viewTabs();
  let inside = "";
  if (state.w) {
    try {
      state.inbox = await api(endpoint("inbox"));
      inside = opPanel();
    } catch (e) {
      if (e.status === 404 && !given) {
        try {
          localStorage.removeItem("tg:last-workspace");
        } catch {}
        state.w = null;
        return operator();
      }
      if (e.status !== 403) throw e;
      inside =
        '<section class="panel"><h2>관객 초대 링크로 접속했습니다</h2><p>이 공간의 접수함은 개설한 운영자 브라우저에서 열 수 있습니다.</p><div class="actions">' +
        button("guest", "내 관객 화면 열기") +
        " " +
        button("create", "새 운영자 시연 공간 만들기") +
        "</div></section>";
    }
  }
  if (!inside)
    inside =
      '<section class="panel"><h2>운영자 시연 시작</h2><p>개인 시연 공간을 만들면 이 브라우저에만 운영자 권한을 발급합니다. 관객 링크는 별도로 공유할 수 있습니다.</p><div class="actions">' +
      button("create", "운영자 시연 공간 만들기", true) +
      "</div></section>";
  app.innerHTML =
    intro(
      "운영자 접수함",
      "관객 접수와 예매 기록을 대조하고, 소명과 승인 결과를 확인하세요.",
      "운영자 전용",
    ) + inside;
}
function navigate() {
  const u = new URL("/", location.origin);
  if (state.w) u.searchParams.set("w", state.w);
  if (state.role === "operator") u.searchParams.set("view", "operator");
  history.replaceState(null, "", u);
}
async function doAction(action) {
  notice.textContent = "";
  if (action === "analyze") {
    state.analyzed = true;
    audience();
    return;
  }
  if (action === "create") {
    const x = await api("/api/workspaces", {});
    state.w = x.id;
    try {
      localStorage.setItem("tg:last-workspace", x.id);
    } catch {}
    state.item = "hanbit";
    navigate();
    state.role === "operator" ? await operator() : audience();
    return;
  }
  if (action === "submit") {
    const ev = [...document.querySelectorAll("[name=evidence]:checked")].map(
      (e) => Number(e.value),
    );
    if (!document.querySelector("#consent").checked || !ev.length)
      throw Error("근거 문구와 전송 동의를 확인하세요.");
    const index = key("send-" + ev.join(","));
    let id = sessionStorage.getItem(index);
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem(index, id);
    }
    const r = await api(endpoint("receipts"), {
      source: state.data.hanbit.source,
      consent: true,
      evidence: ev,
      key: id,
    });
    sessionStorage.setItem(key("receipt"), JSON.stringify(r.receipt));
    audience();
    notice.textContent =
      "운영자에게 접수했습니다. 아래에서 접수번호를 확인하세요.";
    return;
  }
  if (action === "copy") {
    const input = document.querySelector("#invite");
    try {
      await navigator.clipboard.writeText(input.value);
      notice.textContent = "관객 초대 링크를 복사했습니다.";
    } catch {
      input.select();
      notice.textContent = "선택한 링크를 복사해 주세요.";
    }
    return;
  }
  if (action === "guest") {
    state.item = "hanbit";
    audience();
    navigate();
    return;
  }
  if (action === "refresh") {
    await operator();
    return;
  }
  if (["explain", "reply", "elapse", "approve"].includes(action)) {
    const body =
      action === "approve"
        ? { approved: document.querySelector("#approval")?.checked === true }
        : {};
    await api(endpoint(action), body);
    await operator();
    return;
  }
}
function showError(e) {
  notice.textContent = e.message;
}
app.addEventListener("click", async (ev) => {
  const target = ev.target.closest("button");
  if (!target) return;
  if (target.dataset.case) {
    notice.textContent = "";
    state.item = target.dataset.case;
    state.analyzed = false;
    audience();
    return;
  }
  if (!target.dataset.action || app.inert) return;
  app.inert = true;
  target.disabled = true;
  try {
    await doAction(target.dataset.action);
  } catch (e) {
    showError(e);
  } finally {
    app.inert = false;
    target.disabled = false;
  }
});
document.querySelector("#audience").onclick = () => {
  if (!state.data) return;
  notice.textContent = "";
  audience();
  navigate();
};
document.querySelector("#operator").onclick = async () => {
  if (!state.data) return;
  notice.textContent = "";
  try {
    await operator();
    navigate();
  } catch (e) {
    showError(e);
  }
};
(async () => {
  try {
    state.data = await api("/api/samples");
    if (given) await api(endpoint("guest"));
    state.role === "operator" ? await operator() : audience();
  } catch (e) {
    showError(e);
    app.textContent =
      "링크를 확인하거나 상단 서비스 이름을 눌러 처음부터 다시 열어 주세요.";
  }
})();

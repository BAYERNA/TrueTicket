// Public samples are produced by the original Python analyzer. Only this module reads operator fixtures.
const DAY = 86400000;
const responseHeaders = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Cache-Control": "no-store",
};
const json = (data, status = 200, extra = {}) =>
  new Response(JSON.stringify(data), {
    status,
    headers: {
      ...responseHeaders,
      "Content-Type": "application/json; charset=utf-8",
      ...extra,
    },
  });
class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}
const reject = (status, message) => {
  throw new HttpError(status, message);
};
const stmt = (db, sql, ...params) => db.prepare(sql).bind(...params);
const list = async (q) => (await q.all()).results;
const cleanId = /^[0-9a-f-]{36}$/;
const uuid = () => crypto.randomUUID();
async function hash(value) {
  const bytes = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value),
  );
  return Array.from(new Uint8Array(bytes), (b) =>
    b.toString(16).padStart(2, "0"),
  ).join("");
}
function cookie(id) {
  return "tg_op_" + id.replaceAll("-", "");
}
async function readBody(req) {
  if (!req.headers.get("Content-Type")?.startsWith("application/json"))
    reject(415, "JSON 요청이 필요합니다.");
  if (
    req.headers.get("Origin") &&
    req.headers.get("Origin") !== new URL(req.url).origin
  )
    reject(403, "같은 서비스에서 다시 시도하세요.");
  const raw = await req.text();
  if (raw.length > 4096) reject(413, "요청이 너무 깁니다.");
  try {
    const b = JSON.parse(raw);
    if (!b || Array.isArray(b) || typeof b !== "object") throw Error();
    return b;
  } catch {
    reject(400, "요청 내용을 확인해 주세요.");
  }
}
async function workspace(db, id) {
  if (!cleanId.test(id)) reject(404, "시연 공간을 찾을 수 없습니다.");
  const w = await stmt(db, "SELECT * FROM workspaces WHERE id=?", id).first();
  if (!w) reject(404, "시연 공간을 찾을 수 없습니다.");
  return w;
}
async function requireOrganizer(req, w) {
  const prefix = cookie(w.id) + "=";
  const token = (req.headers.get("Cookie") || "")
    .split(";")
    .map((v) => v.trim())
    .find((v) => v.startsWith(prefix))
    ?.slice(prefix.length);
  if (
    !token ||
    (await hash(token)) !== w.session_hash ||
    Date.now() > w.created_at + 30 * DAY
  )
    reject(403, "이 공간을 만든 운영자 세션에서 열어 주세요.");
}
function privateMatch() {
  const bookings = HANBIT.seats
    .map((seat) => BOOKINGS.find((b) => b.seat === seat))
    .filter(Boolean);
  const scores = bookings.map((b) => b.score);
  const surplus = bookings.filter((b) => HANBIT.asking > b.paid).length;
  return {
    bookings,
    high: surplus >= 2 && scores.some((score) => score >= 0.8),
  };
}
function assignments(bookings) {
  const queue = WAITLIST.slice().sort((a, b) =>
    a.joined.localeCompare(b.joined),
  );
  const rows = [];
  for (const b of bookings) {
    const i = queue.findIndex((f) => f.grade === b.grade);
    if (i < 0) continue;
    rows.push({
      seat: b.seat,
      fan: queue.splice(i, 1)[0].id,
      price: HANBIT.listed,
    });
  }
  return rows;
}
async function inbox(db, id) {
  const w = await workspace(db, id);
  const rows = await list(
    stmt(
      db,
      "SELECT id,evidence,created_at FROM receipts WHERE workspace_id=? ORDER BY created_at,id",
      id,
    ),
  );
  const { bookings, high } = privateMatch();
  return {
    id,
    caseId: "case-" + HANBIT.source,
    source: HANBIT.source,
    session: HANBIT.session,
    state: w.state,
    deadline: w.deadline,
    high,
    bookings: bookings.map((b) => ({
      ...b,
      difference: HANBIT.asking - b.paid,
    })),
    receipts: rows.map((r) => ({
      receipt: r.id,
      evidence: JSON.parse(r.evidence).map((i) => HANBIT.evidence[i]),
      time: r.created_at,
    })),
    offers: await list(
      stmt(
        db,
        "SELECT seat,fan,price FROM offers WHERE workspace_id=? ORDER BY seat",
        id,
      ),
    ),
  };
}
async function receive(db, w, b) {
  if (b.consent !== true) reject(422, "선택 문구 전송에 동의해야 합니다.");
  if (
    b.source !== HANBIT.source ||
    !cleanId.test(b.key || "") ||
    !Array.isArray(b.evidence) ||
    !b.evidence.length ||
    b.evidence.some(
      (i) => !Number.isInteger(i) || i < 0 || i >= HANBIT.evidence.length,
    )
  )
    reject(422, "선택한 사례와 근거를 확인하세요.");
  const evidence = JSON.stringify([...new Set(b.evidence)].sort());
  const id = "TG-" + uuid();
  const now = Date.now();
  await stmt(
    db,
    "INSERT INTO receipts(id,workspace_id,idem,evidence,created_at) VALUES (?,?,?,?,?) ON CONFLICT(workspace_id,idem) DO NOTHING",
    id,
    w.id,
    b.key,
    evidence,
    now,
  ).run();
  const row = await stmt(
    db,
    "SELECT id,evidence FROM receipts WHERE workspace_id=? AND idem=?",
    w.id,
    b.key,
  ).first();
  if (row.evidence !== evidence)
    reject(409, "같은 요청번호에 다른 근거가 포함되어 있습니다.");
  return json(
    {
      receipt: row.id,
      organizer: HANBIT.organizer,
      source: HANBIT.source,
      accepted: true,
    },
    row.id === id ? 201 : 200,
  );
}
async function advance(db, w, action, b) {
  const now = Date.now();
  const update = (sql, ...args) => stmt(db, sql, ...args).run();
  let moved, desired;
  if (action === "explain") {
    desired = "awaiting";
    moved = await update(
      "UPDATE workspaces SET state='awaiting', deadline=? WHERE id=? AND state='open' AND EXISTS(SELECT 1 FROM receipts WHERE workspace_id=?)",
      now + DAY,
      w.id,
      w.id,
    );
  } else if (action === "reply") {
    desired = "appealed";
    moved = await update(
      "UPDATE workspaces SET state='appealed' WHERE id=? AND state='awaiting'",
      w.id,
    );
  } else if (action === "elapse") {
    desired = "awaiting";
    moved = await update(
      "UPDATE workspaces SET deadline=? WHERE id=? AND state='awaiting'",
      now - 1,
      w.id,
    );
  } else if (action === "approve") {
    if (b.approved !== true) reject(422, "별도의 운영자 승인이 필요합니다.");
    const match = privateMatch();
    if (!match.high) reject(409, "고위험 조건을 충족하지 않았습니다.");
    const jobs = [
      stmt(
        db,
        "UPDATE workspaces SET state='offered',completed_at=? WHERE id=? AND state='awaiting' AND deadline<=?",
        now,
        w.id,
        now,
      ),
    ];
    for (const a of assignments(match.bookings)) {
      jobs.push(
        stmt(
          db,
          "INSERT INTO offers(workspace_id,seat,fan,price) SELECT id,?,?,? FROM workspaces WHERE id=? AND state='offered' ON CONFLICT DO NOTHING",
          a.seat,
          a.fan,
          a.price,
          w.id,
        ),
      );
    }
    const [transition] = await db.batch(jobs);
    moved = transition;
    desired = "offered";
  } else reject(404, "동작을 찾을 수 없습니다.");
  const after = await inbox(db, w.id);
  if (!moved.meta.changes && after.state !== desired)
    reject(409, "현재 단계에서는 이 처리를 할 수 없습니다.");
  return json(after);
}
const labels = {
  facts: "확인된 사실",
  signals: "의심 정황",
  unknowns: "확인 불가",
  actions: "권고 행동",
};
function download(sample) {
  const r = sample.report;
  const parts = [
    "TicketGuard AI | 거래 전 점검",
    sample.name + " · " + sample.date,
    "가상 시연 · 프리셋 · " + r.level,
    "",
  ];
  for (const [key, title] of Object.entries(labels))
    parts.push(
      "[" + title + "]",
      ...(r[key].length ? r[key] : ["표시할 항목이 없습니다."]).map(
        (x) => "- " + x,
      ),
      "",
    );
  parts.push(
    "가격 근거  " + r.benchmark_source,
    "정책 근거  " + r.policy_source,
    "공식 신고센터  https://www.culture.go.kr/singo/",
  );
  return new Response("\uFEFF" + parts.join("\r\n"), {
    headers: {
      ...responseHeaders,
      "Content-Type": "text/plain; charset=utf-8",
      "Content-Disposition":
        'attachment; filename="TicketGuard_AI_' + sample.id + '.txt"',
    },
  });
}
export default {
  async fetch(req, env) {
    try {
      const p = new URL(req.url).pathname;
      const method = req.method;
      if (method === "GET") {
        if (p === "/" || p === "/style.css" || p === "/client.js") {
          const [body, type] =
            p === "/"
              ? [PAGE, "text/html"]
              : p === "/style.css"
                ? [STYLE, "text/css"]
                : [CLIENT, "text/javascript"];
          return new Response(body, {
            headers: {
              ...responseHeaders,
              "Content-Type": type + "; charset=utf-8",
              "Content-Security-Policy":
                "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'",
            },
          });
        }
        if (p === "/api/samples")
          return json({ samples: SAMPLES, hanbit: HANBIT });
        const match = p.match(/^\/reports\/([A-Z-]+)\.txt$/);
        if (match) {
          const s = SAMPLES.find((v) => v.id === match[1]);
          if (s) return download(s);
        }
      }
      if (method === "POST" && p === "/api/workspaces") {
        await readBody(req);
        const id = uuid(),
          token = uuid() + uuid(),
          now = Date.now();
        await stmt(
          env.DB,
          "INSERT INTO workspaces(id,session_hash,created_at) VALUES (?,?,?)",
          id,
          await hash(token),
          now,
        ).run();
        return json({ id }, 201, {
          "Set-Cookie":
            cookie(id) +
            "=" +
            token +
            "; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=2592000",
        });
      }
      const match = p.match(
        /^\/api\/workspaces\/([a-f0-9-]+)\/(guest|receipts|inbox|explain|reply|elapse|approve)$/,
      );
      if (match) {
        const [, id, verb] = match,
          w = await workspace(env.DB, id);
        if (method === "GET" && verb === "guest")
          return json({ id, organizer: HANBIT.organizer });
        if (method === "POST" && verb === "receipts")
          return receive(env.DB, w, await readBody(req)).catch((e) =>
            handleError(e),
          );
        await requireOrganizer(req, w);
        if (method === "GET" && verb === "inbox")
          return json(await inbox(env.DB, id));
        if (
          method === "POST" &&
          ["explain", "reply", "elapse", "approve"].includes(verb)
        )
          return await advance(env.DB, w, verb, await readBody(req));
      }
      return json({ error: "페이지를 찾을 수 없습니다." }, 404);
    } catch (e) {
      return handleError(e);
    }
  },
};
function handleError(e) {
  return json(
    {
      error:
        e instanceof HttpError
          ? e.message
          : "서비스를 불러올 수 없습니다. 잠시 후 다시 시도하세요.",
    },
    e instanceof HttpError ? e.status : 503,
  );
}

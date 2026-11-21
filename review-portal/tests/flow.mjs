import { test } from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import web from "../dist/server/index.js";
const schema = readFileSync(
  new URL("../drizzle/0000_review.sql", import.meta.url),
  "utf8",
);
function connect(file) {
  const sqlite = new DatabaseSync(file);
  const binding = {
    prepare(sql) {
      return {
        bind(...values) {
          return {
            first: async () => sqlite.prepare(sql).get(...values),
            all: async () => ({ results: sqlite.prepare(sql).all(...values) }),
            run: async () => ({
              meta: { changes: sqlite.prepare(sql).run(...values).changes },
            }),
          };
        },
      };
    },
    async batch(statements) {
      sqlite.exec("BEGIN IMMEDIATE");
      try {
        const result = [];
        for (const op of statements) result.push(await op.run());
        sqlite.exec("COMMIT");
        return result;
      } catch (e) {
        sqlite.exec("ROLLBACK");
        throw e;
      }
    },
  };
  return { sqlite, binding };
}
function harness(file = ":memory:", init = true) {
  const { sqlite, binding } = connect(file);
  if (init) sqlite.exec(schema);
  async function query(path, b, auth = "") {
    const headers =
      b === undefined ? {} : { "Content-Type": "application/json" };
    if (auth) headers.Cookie = auth;
    const req = new Request("https://demo.invalid" + path, {
      method: b === undefined ? "GET" : "POST",
      headers,
      body: b === undefined ? undefined : JSON.stringify(b),
    });
    const r = await web.fetch(req, { DB: binding });
    return {
      r,
      status: r.status,
      body: r.headers.get("Content-Type")?.startsWith("application/json")
        ? await r.clone().json()
        : await r.clone().text(),
    };
  }
  async function create() {
    const { r, body, status } = await query("/api/workspaces", {});
    assert.equal(status, 201);
    const value = r.headers.get("Set-Cookie");
    assert.match(value, /HttpOnly; Secure/);
    return { id: body.id, cookie: value.split(";")[0] };
  }
  return { query, create, close: () => sqlite.close() };
}
const data = () => ({
  key: crypto.randomUUID(),
  source: "post-017",
  consent: true,
  evidence: [0, 2],
});
const path = (w, verb) => "/api/workspaces/" + w.id + "/" + verb;
test("세 익명 사례, 원래 상태, 네 구획 TXT와 비공개 필드 분리", async () => {
  const h = harness(),
    s = await h.query("/api/samples");
  assert.equal(s.status, 200);
  assert.deepEqual(
    s.body.samples.map((x) => [x.id, x.report.level, x.report.premium_krw]),
    [
      ["SP-FEST", "CAUTION", 180000],
      ["SP-MUS", "CAUTION", 0],
      ["SP-BASE", "REVIEW", 0],
    ],
  );
  assert.equal(s.body.hanbit.asking - s.body.hanbit.listed, 27000);
  for (const x of s.body.samples) {
    const t = await h.query("/reports/" + x.id + ".txt");
    assert.equal(t.status, 200);
    assert.match(t.r.headers.get("Content-Disposition"), /attachment/);
    for (const part of ["확인된 사실", "의심 정황", "확인 불가", "권고 행동"])
      assert.ok(t.body.includes(part));
  }
  for (const p of ["/", "/client.js", "/api/samples"]) {
    const { body } = await h.query(p);
    assert.doesNotMatch(
      JSON.stringify(body),
      /booking-0001|112000|fan-001|account-001/,
    );
  }
  h.close();
});
test("수신 동의, 선택 근거 제한, 재전송·충돌 및 기존 운영 사례 연결", async () => {
  const h = harness(),
    w = await h.create(),
    d = data();
  assert.equal(
    (await h.query(path(w, "receipts"), { ...d, consent: false })).status,
    422,
  );
  assert.equal(
    (await h.query(path(w, "receipts"), { ...d, evidence: [9] })).status,
    422,
  );
  const a = await h.query(path(w, "receipts"), d),
    b = await h.query(path(w, "receipts"), { ...d, evidence: [2, 0] });
  assert.equal(a.status, 201);
  assert.equal(b.status, 200);
  assert.equal(a.body.receipt, b.body.receipt);
  assert.equal(
    (await h.query(path(w, "receipts"), { ...d, evidence: [1] })).status,
    409,
  );
  const other = await h.query(path(w, "receipts"), data());
  assert.notEqual(other.body.receipt, b.body.receipt);
  const { body } = await h.query(path(w, "inbox"), undefined, w.cookie);
  assert.deepEqual(
    body.receipts.map((x) => x.receipt).sort(),
    [a.body.receipt, other.body.receipt].sort(),
  );
  assert.equal(body.caseId, "case-post-017");
  assert.deepEqual(
    body.bookings.map((x) => [x.booking, x.paid, x.difference, x.score]),
    [
      ["booking-0001", 112000, 25000, 0.84],
      ["booking-0002", 112000, 25000, 0.84],
    ],
  );
  h.close();
});
test("다른 운영자와 관객은 접수함 조회와 상태 변경 권한 없음", async () => {
  const h = harness(),
    a = await h.create(),
    b = await h.create();
  for (const auth of ["", b.cookie]) {
    assert.equal(
      (await h.query(path(a, "inbox"), undefined, auth)).status,
      403,
    );
    for (const verb of ["explain", "reply", "elapse", "approve"])
      assert.equal((await h.query(path(a, verb), {}, auth)).status, 403);
  }
  const g = await h.query(path(a, "guest"));
  assert.deepEqual(Object.keys(g.body).sort(), ["id", "organizer"]);
  h.close();
});
test("접수·기한·별도 승인 게이트와 승인 재시도 시 두 좌석별 정가 안내 1회", async () => {
  const h = harness(),
    w = await h.create(),
    act = (v, b = {}) => h.query(path(w, v), b, w.cookie);
  assert.equal((await act("explain")).status, 409);
  await h.query(path(w, "receipts"), data());
  await act("explain");
  assert.equal((await act("approve", { approved: true })).status, 409);
  await act("elapse");
  assert.equal((await act("approve")).status, 422);
  const a = await act("approve", { approved: true }),
    b = await act("approve", { approved: true });
  assert.equal(a.status, 200);
  assert.deepEqual(a.body.offers, [
    { seat: "A-01-01", fan: "fan-001", price: 110000 },
    { seat: "A-01-02", fan: "fan-003", price: 110000 },
  ]);
  assert.deepEqual(b.body.offers, a.body.offers);
  h.close();
});
test("소명 접수 후 기한 경과 또는 승인 버튼을 다시 시도해도 재배분 중단", async () => {
  const h = harness(),
    w = await h.create(),
    act = (v, b = {}) => h.query(path(w, v), b, w.cookie);
  await h.query(path(w, "receipts"), data());
  await act("explain");
  await act("elapse");
  await act("reply");
  assert.equal((await act("approve", { approved: true })).status, 409);
  assert.equal((await act("elapse")).status, 409);
  const { body } = await h.query(path(w, "inbox"), undefined, w.cookie);
  assert.equal(body.state, "appealed");
  assert.equal(body.offers.length, 0);
  h.close();
});
test("SQLite 재시작 후 같은 관객 링크·접수번호·운영자 세션·시드 재조회", async () => {
  const dir = mkdtempSync(join(tmpdir(), "tg-"));
  try {
    const file = join(dir, "review.sqlite");
    let h = harness(file);
    const w = await h.create(),
      d = data(),
      a = await h.query(path(w, "receipts"), d);
    h.close();
    h = harness(file, false);
    const b = await h.query(path(w, "receipts"), d);
    assert.equal(b.body.receipt, a.body.receipt);
    assert.equal(
      (await h.query(path(w, "inbox"), undefined, w.cookie)).body.receipts
        .length,
      1,
    );
    assert.equal((await h.query("/api/samples")).body.samples.length, 3);
    h.close();
  } finally {
    rmSync(dir, { recursive: true });
  }
});

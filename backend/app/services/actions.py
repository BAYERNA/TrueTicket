from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

from fastapi import HTTPException

from ..agent.pii import mask_pii
from .analysis import RULES


ACTION_LABELS = {
    "request_explanation": "소명 요청", "close_normal": "정상 처리",
    "cancel_redistribute": "예매 취소·정가 재배분", "draft_report": "신고서 초안",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_case(db, case_id: str) -> dict:
    case = db.get_case(case_id)
    if case is None:
        raise HTTPException(404, "케이스를 찾을 수 없습니다.")
    return case


def history_lines(actions: list[dict]) -> list[str]:
    lines = []
    for action in actions:
        if action["type"] == "approval_requested":
            continue
        lines.append(f"{action['at']} · {action['type']} · {action.get('actor', 'demo-system')}")
        for offer in action.get("allocations", []):
            lines.append(f"정가 재배분 안내 · {offer['fan_id']} · {offer['seat']} · {offer['price']:,}원")
    return lines


def draft_document(case: dict, kind: str) -> dict:
    if kind == "draft_report":
        actions = case["actions"]
        for index in range(len(actions) - 1, -1, -1):
            approved = actions[index]
            if approved["type"] == kind and approved.get("approved") and approved.get("document"):
                document = approved["document"]
                subsequent = history_lines(actions[index + 1:])
                if subsequent:
                    return {**document, "text": "\n".join([document["text"], "", "승인 후 처리 경과", *subsequent])}
                return document
    post = case["post"]
    lines = [f"TicketGuard AI {ACTION_LABELS[kind]}", "가상 데이터 기반 운영 검토용 초안", "",
             f"케이스 {case['case_id']}", f"게시글 {post['post_id']} · {post['channel']}",
             post["title"], post["body"], "", "연결된 예매"]
    for booking in case["match"]["bookings"]:
        lines.append(f"{booking['booking_id']} · {booking['account_id']} · {booking['seat']} · 구입가 {booking['price_paid']:,}원 · {booking['booked_at']} · 봇 점수 {booking['bot']['score']:.3f}")
    lines += ["", "같은 판매자 후보로 묶인 글"]
    lines += [f"{peer['post_id']} · {peer['author_handle']} · {peer['title']}" for peer in case["related_posts"]]
    lines += ["", f"위험 등급 {case['risk']['risk_level']}", "충족 규칙"]
    lines += [f"{key} {RULES[key]['label']} · {RULES[key]['description']}" for key in case["risk"]["rule_hits"]]
    if case["explanation"]["generated_by_ai"]:
        lines += ["", "AI가 생성한 답변", case["explanation"]["text"]]
    if kind == "request_explanation":
        lines += ["", "예매 내역과 양도 조건에 대한 소명을 요청합니다. 운영자가 내용을 검토한 뒤 후속 조치를 결정합니다.",
                  "요청·발송과 회신은 이 데모 안에서 시뮬레이션합니다."]
    elif kind == "cancel_redistribute":
        lines += ["", "소명 기한 경과를 확인한 후 연결된 예매를 취소하고, 좌석 등급별 대기 순서에 따라 정가 구매 안내를 생성합니다."]
    elif kind == "close_normal":
        lines += ["", "소명 검토 결과를 반영해 정상 종료하며, 오탐 기록을 남깁니다."]
    lines += ["", "처리 경과", *history_lines(case["actions"])]
    return {"type": kind, "text": "\n".join(lines), "generated_by_ai": case["explanation"]["generated_by_ai"],
            "source": "validated_template", "simulation": True}


def prepare_approval(db, case_id: str, kind: str) -> dict:
    case = require_case(db, case_id)
    document = draft_document(case, kind)
    approval_id = uuid4().hex
    event = {"type": "approval_requested", "action_type": kind, "approval_id": approval_id,
             "at": now(), "actor": "demo-operator", "document": document}
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT actions FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "케이스를 찾을 수 없습니다.")
        actions = json.loads(row["actions"])
        actions.append(event)
        connection.execute("UPDATE cases SET actions = ? WHERE case_id = ?", (json.dumps(actions, ensure_ascii=False), case_id))
    return {"case_id": case_id, "type": kind, "approval_id": approval_id, "document": document}


def execute_action(db, state: dict) -> dict:
    case_id, kind, approval_id = state["case_id"], state["type"], state["approval_id"]
    approval = state.get("approval") or {}
    if approval.get("approved") is not True:
        raise HTTPException(403, "운영자 승인이 필요합니다.")
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT c.*, a.details FROM cases c JOIN analyses a USING(post_id) WHERE case_id = ?", (case_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "케이스를 찾을 수 없습니다.")
        actions = json.loads(row["actions"])
        completed = next((a for a in actions if a.get("approval_id") == approval_id and a["type"] == kind), None)
        if completed:
            return completed
        pending = next((a for a in actions if a["type"] == "approval_requested" and a.get("approval_id") == approval_id and a["action_type"] == kind), None)
        if pending is None:
            raise HTTPException(403, "이 케이스의 승인 요청을 확인할 수 없습니다.")
        record = json.loads(row["details"])
        status = row["status"]
        action = {"type": kind, "approval_id": approval_id, "approved": True, "actor": "demo-operator",
                  "at": now(), "simulation": True,
                  "document": {**pending["document"], "text": mask_pii(approval.get("edited_text") or pending["document"]["text"]).text}}
        if kind == "request_explanation":
            if status != "신규" or record["risk"]["risk_level"] not in {"높음", "중간"}:
                raise HTTPException(409, "신규 의심 케이스에서 소명을 요청할 수 있습니다.")
            status = "소명 대기"
            action["deadline"] = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        elif kind == "close_normal":
            if status not in {"신규", "소명 대기"}:
                raise HTTPException(409, "진행 중인 케이스에서 정상 처리할 수 있습니다.")
            status = "정상 종료"
            action["false_positive"] = record["risk"]["risk_level"] in {"높음", "중간"}
        elif kind == "cancel_redistribute":
            if status != "소명 대기" or record["risk"]["risk_level"] != "높음":
                raise HTTPException(409, "소명 대기 중인 높은 위험 케이스에서 취소할 수 있습니다.")
            if any(a["type"] == "explanation_received" for a in actions):
                raise HTTPException(409, "접수된 소명을 검토한 뒤 정상 처리해 주세요.")
            requested = next(a for a in reversed(actions) if a["type"] == "request_explanation")
            expired = any(a["type"] == "deadline_elapsed" for a in actions) or datetime.now(timezone.utc) >= datetime.fromisoformat(requested["deadline"])
            if not expired:
                raise HTTPException(409, "소명 기한 경과를 먼저 확인해 주세요.")
            ids = record["match"]["matched_booking_ids"]
            if not ids:
                raise HTTPException(409, "취소할 연결 예매가 없습니다.")
            allocations = []
            for booking_id in ids:
                booking = connection.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
                if booking is None or booking["status"] != "confirmed":
                    raise HTTPException(409, "예매 상태가 바뀌었습니다. 다른 케이스의 처리 이력을 확인해 주세요.")
                connection.execute("UPDATE bookings SET status = 'cancelled' WHERE booking_id = ?", (booking_id,))
                waiter = connection.execute(
                    "SELECT * FROM waitlist WHERE event_id = ? AND grade = ? AND status = 'waiting' ORDER BY joined_at, fan_id LIMIT 1",
                    (booking["event_id"], booking["grade"]),
                ).fetchone()
                if waiter:
                    event = connection.execute("SELECT seat_grades FROM events WHERE id = ?", (booking["event_id"],)).fetchone()
                    price = json.loads(event["seat_grades"])[booking["grade"]]
                    connection.execute("UPDATE waitlist SET status = 'offered' WHERE fan_id = ?", (waiter["fan_id"],))
                    allocations.append({"booking_id": booking_id, "fan_id": waiter["fan_id"], "seat": booking["seat"],
                                        "grade": booking["grade"], "price": price,
                                        "message": f"{booking['seat']} 좌석을 정가 {price:,}원에 구매할 수 있습니다. 데모 안내입니다."})
            action["cancelled_booking_ids"] = ids
            action["allocations"] = allocations
            status = "취소·재배분"
        actions.append(action)
        connection.execute("UPDATE cases SET status = ?, actions = ? WHERE case_id = ?", (status, json.dumps(actions, ensure_ascii=False), case_id))
        return action


def simulate(db, case_id: str, kind: str, text: str | None) -> dict:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "케이스를 찾을 수 없습니다.")
        if row["status"] != "소명 대기":
            raise HTTPException(409, "소명 대기 상태에서 시뮬레이션할 수 있습니다.")
        actions = json.loads(row["actions"])
        if not any(a["type"] == kind for a in actions):
            actions.append({"type": kind, "at": now(), "actor": "demo-system", "simulation": True,
                            "text": mask_pii(text or "친구 대신 정가로 양도하려던 표입니다.").text if kind == "explanation_received" else "데모 소명 기한 경과"})
            connection.execute("UPDATE cases SET actions = ? WHERE case_id = ?", (json.dumps(actions, ensure_ascii=False), case_id))
    return require_case(db, case_id)

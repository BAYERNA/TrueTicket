import { useState } from "react";
import type { FormEvent } from "react";

import type { Channel, Event, PostDraft } from "../api/market";

type Props = {
  events: Event[];
  disabled: boolean;
  onPost: (draft: PostDraft) => Promise<boolean>;
};

export function PostComposer({ events, disabled, onPost }: Props) {
  const [eventId, setEventId] = useState("");
  const [channel, setChannel] = useState<Channel>("가상 중고거래");
  const [title, setTitle] = useState("");
  const [price, setPrice] = useState("");
  const [body, setBody] = useState("");
  const targetEventId = eventId || events[0]?.id || "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const created = await onPost({
      event_id: targetEventId,
      channel,
      title,
      price: price === "" ? null : Number(price),
      body,
      author_handle: "가상운영자",
    });
    if (created) {
      setTitle("");
      setPrice("");
      setBody("");
    }
  }

  return (
    <section className="panel composer" aria-labelledby="compose-title">
      <h2 id="compose-title">테스트 글 쓰기</h2>
      <form onSubmit={submit}>
        <fieldset disabled={disabled || !events.length}>
          <div className="form-row">
            <label>
              공연
              <select value={targetEventId} onChange={(event) => setEventId(event.target.value)} required>
                {events.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
            <label>
              채널
              <select value={channel} onChange={(event) => setChannel(event.target.value as Channel)}>
                <option>가상 중고거래</option>
                <option>가상 SNS</option>
              </select>
            </label>
          </div>
          <label>
            게시글 제목
            <input autoComplete="off" value={title} onChange={(event) => setTitle(event.target.value)}
              maxLength={160} placeholder="예: 한빛 겨울 콘서트 2장 양도" required />
          </label>
          <label>
              장당 표시 가격 <span className="optional">(선택, 원)</span>
            <input type="number" inputMode="numeric" value={price} onChange={(event) => setPrice(event.target.value)}
              min="0" max="100000000" step="1" placeholder="가격 미정이면 비워두기" />
          </label>
          <label>
            본문
            <textarea value={body} onChange={(event) => setBody(event.target.value)}
              maxLength={3000} rows={4} placeholder="예: A구역 1열 1번, 정가 11만 원에 수고비 3만 원 추가." required />
          </label>
          <p className="muted">감시에 사용할 좌석·수량·판매가는 제목이나 본문에 적어 주세요.</p>
          <button className="primary" type="submit">테스트 글 등록</button>
        </fieldset>
      </form>
    </section>
  );
}

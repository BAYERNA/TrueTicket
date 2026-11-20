import { useEffect, useState } from "react";

import { addPost, fetchEvents, fetchPosts, resetMarket, scanPosts } from "../api/market";
import type { Event, MarketPost, PostDraft, Scan } from "../api/market";
import { PostComposer } from "../components/PostComposer";
import { Header } from "../components/Header";

const won = new Intl.NumberFormat("ko-KR");

export function MarketPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [posts, setPosts] = useState<MarketPost[]>([]);
  const [eventFilter, setEventFilter] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [latestPostId, setLatestPostId] = useState<string | null>(null);
  const [scan, setScan] = useState<Scan | null>(null);

  useEffect(() => {
    Promise.all([fetchEvents(), fetchPosts()]).then(([loadedEvents, loadedPosts]) => {
      setEvents(loadedEvents);
      setPosts(loadedPosts);
    }).catch((reason) => setError(reason.message)).finally(() => setLoading(false));
  }, []);

  async function run(action: () => Promise<void>): Promise<boolean> {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      return true;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "요청을 완료하지 못했습니다.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  function submitPost(draft: PostDraft) {
    return run(async () => {
      const post = await addPost(draft);
      setPosts((current) => [post, ...current]);
      setLatestPostId(post.post_id);
      setQuery("");
      setEventFilter("");
      setNotice("테스트 글을 등록했습니다. 감시를 시작하면 새 글도 수집합니다.");
    });
  }

  function startScan() {
    void run(async () => {
      const result = await scanPosts(eventFilter);
      setScan(result);
      if (result.status === "failed") {
        const detail = result.http_status ? ` (HTTP ${result.http_status})` : "";
        setError(`가상 마켓 피드 조회에 실패했습니다${detail}.`);
      }
    });
  }

  function reset() {
    void run(async () => {
      await resetMarket();
      const initialPosts = await fetchPosts();
      setPosts(initialPosts);
      setQuery("");
      setEventFilter("");
      setLatestPostId(null);
      setScan(null);
      setNotice(`데모를 초기화했습니다. 게시글 ${initialPosts.length}건이 복원되었습니다.`);
    });
  }

  const normalizedQuery = query.trim().toLowerCase();
  const visible = posts.filter((post) =>
    (!eventFilter || post.event_id === eventFilter) &&
    (!normalizedQuery || [post.post_id, post.title, post.author_handle, post.body].some(
      (field) => field.toLowerCase().includes(normalizedQuery),
    )),
  );
  const newPostCollected = latestPostId !== null && scan?.post_ids.includes(latestPostId);

  return (
    <>
      <Header />

      <main className="shell">
        <section className="hero">
          <div>
            <h1>가상 리셀 마켓</h1>
            <p>테스트 글을 등록하고 감시 수집 결과를 확인하세요.</p>
          </div>
          <div className="actions">
            <button type="button" onClick={reset} disabled={busy || loading}>데모 초기화</button>
            <button type="button" className="primary" onClick={startScan} disabled={busy || loading}>감시 시작</button>
          </div>
        </section>

        {error && <p className="message error" role="alert">{error}</p>}
        {(notice || scan?.status === "ok") && (
          <section className="message" aria-live="polite">
            {notice && <p>{notice}</p>}
            {scan?.status === "ok" && <p><strong>HTTP 수집 완료</strong> · {scan.post_count}건</p>}
            {scan?.extraction?.status === "api_key_required" && <p>구조화 추출은 API 키 설정 후 실행할 수 있어요.</p>}
            {scan?.extraction && scan.extraction.status !== "api_key_required" && (
              <p>구조화 추출 {scan.extraction.processed}건 · 다음 단계 가능 {scan.extraction.ready}건 · 확인 불가 {scan.extraction.review}건</p>
            )}
            {newPostCollected && <p>새 테스트 글 수집 확인 <code>{latestPostId}</code></p>}
          </section>
        )}

        <div className="workspace">
          <section className="panel market-list" aria-labelledby="posts-title">
            <div className="panel-heading">
              <h2 id="posts-title">게시글</h2>
              <span className="count">{visible.length}건</span>
            </div>
            <div className="filters">
              <label className="sr-only" htmlFor="event-filter">공연 필터</label>
              <select id="event-filter" value={eventFilter} onChange={(event) => setEventFilter(event.target.value)}>
                <option value="">전체 공연</option>
                {events.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
              <label className="sr-only" htmlFor="post-search">게시글 검색</label>
              <input id="post-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)}
                placeholder="게시글 ID, 제목, 작성자 검색" />
            </div>
            <div className="post-list">
              {loading && <p className="empty">게시글을 불러오는 중입니다.</p>}
              {!loading && visible.length === 0 && <p className="empty">해당하는 게시글이 없습니다.</p>}
              {visible.map((post) => (
                <details className="post" key={post.post_id} id={post.post_id}>
                  <summary>
                    <div className="post-main">
                      <div className="post-meta">
                        <span className="channel">{post.channel}</span><code>{post.post_id}</code>
                      </div>
                      <h3>{post.title}</h3>
                    </div>
                    <span className={post.price === null ? "price unspecified" : "price"}>
                      {post.price === null ? "가격 미등록" : `${won.format(post.price)}원`}
                    </span>
                  </summary>
                  <div className="post-body">
                    <p>{post.body}</p>
                    <span>{post.author_handle} · {post.created_at.slice(0, 10)}</span>
                  </div>
                </details>
              ))}
            </div>
          </section>
          <PostComposer events={events} disabled={busy || loading} onPost={submitPost} />
        </div>
      </main>
    </>
  );
}

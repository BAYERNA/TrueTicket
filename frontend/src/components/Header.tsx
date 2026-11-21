export function Header() {
  const path = window.location.pathname;
  return <header className="topbar"><div className="shell topbar-inner">
    <a href="/" className="brand"><span className="brand-mark" aria-hidden="true">T</span>TicketGuard AI</a>
    <nav aria-label="주 메뉴">
      <a href="/" aria-current={path === "/" ? "page" : undefined}>대시보드</a>
      <a href="/cases" aria-current={path.startsWith("/cases") ? "page" : undefined}>의심 큐</a>
      <a href="/market" aria-current={path === "/market" ? "page" : undefined}>가상 마켓</a>
      <a href="https://ticketguard-ai-demo.tart-hippo-0446.chatgpt.site/?view=operator">관객 접수함</a>
    </nav><span className="demo-label">가상 데이터 데모</span>
  </div></header>;
}

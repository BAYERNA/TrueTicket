import { createRoot } from "react-dom/client";

import { MarketPage } from "./pages/MarketPage";
import { Dashboard } from "./pages/Dashboard";
import { CasePage } from "./pages/CasePage";
import "./styles.css";

const path = window.location.pathname;
const detail = path.match(/^\/cases\/([^/]+)$/);
document.title = `${path === "/market" ? "가상 리셀 마켓" : detail ? "케이스 상세" : path === "/cases" ? "의심 큐" : "암표 대응 대시보드"} | TicketGuard AI`;
createRoot(document.getElementById("root")!).render(
  path === "/market" ? <MarketPage /> : detail ? <CasePage caseId={decodeURIComponent(detail[1])} /> : <Dashboard />,
);

import { setupServer } from "msw/node";

// 핸들러는 비어있는 채로 시작하고, 각 테스트가 필요한 요청만 server.use(...)로 등록한다.
export const server = setupServer();

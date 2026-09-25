"use client";

import { useEffect, useRef, useState } from "react";
import { io, type Socket } from "socket.io-client";
import type { QueueStatusResponse } from "@/types/domain";

const SOCKET_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

export type QueueSocketState = "connecting" | "connected" | "unavailable";

/**
 * queue-service는 아직 Socket.IO(또는 호환) 서버를 노출하지 않는다. 이 훅은 그래도
 * 실제로 연결을 시도하고, 몇 차례 재시도 후에도 실패하면 정직하게 "unavailable"로
 * 내려간다 — 연결된 것처럼 흉내 내지 않는다. 화면은 이 훅의 성공 여부와 무관하게
 * 항상 REST 폴링을 폴백으로 유지해야 한다.
 */
export function useQueueSocket(eventId: string, enabled: boolean) {
  const [connectionState, setConnectionState] = useState<QueueSocketState>("connecting");
  const [liveStatus, setLiveStatus] = useState<QueueStatusResponse | null>(null);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // enabled는 유저가 대기열에 참여한 뒤로만 true가 되고 다시 꺼지지 않으므로, 비활성
    // 상태의 기본값은 useState 초기값("connecting"/null)으로 충분하다 — 여기서 되돌릴
    // 필요가 없다.
    if (!enabled) return;

    const socket = io(SOCKET_BASE_URL, {
      path: "/socket.io",
      reconnectionAttempts: 3,
      timeout: 4000,
    });
    socketRef.current = socket;

    socket.on("connect", () => setConnectionState("connected"));
    socket.on(`queue:${eventId}`, (status: QueueStatusResponse) => setLiveStatus(status));
    socket.on("connect_error", () => setConnectionState("unavailable"));
    socket.io.on("reconnect_failed", () => setConnectionState("unavailable"));

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [eventId, enabled]);

  return { connectionState, liveStatus };
}

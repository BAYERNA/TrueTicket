package com.trueticket.queue.event

/** 대기열 상태가 바뀌었을 때(참여/입장 허용) 발행된다 — Socket.IO 계층이 이를 구독해 실시간으로 푸시한다. */
class QueueChangedEvent(val eventId: String)

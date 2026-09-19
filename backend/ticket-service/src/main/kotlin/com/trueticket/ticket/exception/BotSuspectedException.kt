package com.trueticket.ticket.exception

import java.util.UUID

/** FR-004: bot-detection-service가 취득 부정성 스코어를 임계치 이상으로 판정한 세션의 예매 시도. */
class BotSuspectedException(reservationSessionId: UUID) :
    RuntimeException("Bot-like behavior detected for session: $reservationSessionId")

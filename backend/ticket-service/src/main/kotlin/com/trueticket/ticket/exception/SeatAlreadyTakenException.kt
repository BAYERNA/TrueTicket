package com.trueticket.ticket.exception

import java.util.UUID

/**
 * 좌석 Optimistic Lock 충돌(동시 선점 시도) 또는 이미 AVAILABLE 상태가 아닌 좌석에
 * 대한 예매 요청 시 발생한다. 컨트롤러 계층에서 409 Conflict로 변환한다.
 */
class SeatAlreadyTakenException(seatId: UUID) : RuntimeException("Seat already taken: $seatId")

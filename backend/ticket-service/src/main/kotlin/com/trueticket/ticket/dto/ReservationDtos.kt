package com.trueticket.ticket.dto

import com.trueticket.ticket.domain.ReservationStatus
import jakarta.validation.constraints.NotNull
import java.time.Instant
import java.util.UUID

data class CreateReservationRequest(
    @field:NotNull val eventId: UUID,
    @field:NotNull val seatId: UUID,
    /** FR-004: bot-detection-service에 스코어를 조회할 때 쓰는 조인 키. 좌석 선택 화면 진입 시 프론트에서 발급한다. */
    @field:NotNull val reservationSessionId: UUID,
)

data class AuthenticatedReservationRequest(
    val userId: UUID,
    val eventId: UUID,
    val seatId: UUID,
    val reservationSessionId: UUID,
)

data class ReservationResponse(
    val reservationId: UUID,
    val userId: UUID,
    val eventId: UUID,
    val seatId: UUID,
    val status: ReservationStatus,
    val qrCode: String?,
    val reservedAt: Instant,
    val expiresAt: Instant,
)

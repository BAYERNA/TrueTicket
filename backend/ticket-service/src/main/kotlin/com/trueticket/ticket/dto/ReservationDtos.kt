package com.trueticket.ticket.dto

import com.trueticket.ticket.domain.ReservationStatus
import jakarta.validation.constraints.NotNull
import java.time.Instant
import java.util.UUID

data class CreateReservationRequest(
    @field:NotNull val userId: UUID,
    @field:NotNull val eventId: UUID,
    @field:NotNull val seatId: UUID,
)

data class ReservationResponse(
    val reservationId: UUID,
    val userId: UUID,
    val eventId: UUID,
    val seatId: UUID,
    val status: ReservationStatus,
    val qrCode: String?,
    val reservedAt: Instant,
)

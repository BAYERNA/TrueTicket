package com.trueticket.ticket.service

import com.trueticket.ticket.domain.Reservation
import com.trueticket.ticket.domain.ReservationStatus
import com.trueticket.ticket.domain.SeatStatus
import com.trueticket.ticket.dto.CreateReservationRequest
import com.trueticket.ticket.dto.ReservationResponse
import com.trueticket.ticket.exception.SeatAlreadyTakenException
import com.trueticket.ticket.repository.ReservationRepository
import com.trueticket.ticket.repository.SeatRepository
import org.springframework.dao.OptimisticLockingFailureException
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.util.UUID

@Service
class ReservationService(
    private val seatRepository: SeatRepository,
    private val reservationRepository: ReservationRepository,
) {

    /**
     * FR-002-1: 좌석은 @Version 기반 Optimistic Lock으로 보호된다. 두 트랜잭션이
     * 동시에 같은 좌석을 읽고 저장하려 하면, 나중에 flush 되는 트랜잭션이
     * OptimisticLockingFailureException을 받는다. 여기서는 재시도 없이 즉시
     * "이미 선점된 좌석"으로 응답하여 사용자에게 다른 좌석을 고르도록 안내한다.
     */
    @Transactional
    fun reserve(request: CreateReservationRequest): ReservationResponse {
        val seat = seatRepository.findById(request.seatId)
            .orElseThrow { SeatAlreadyTakenException(request.seatId) }

        if (seat.status != SeatStatus.AVAILABLE) {
            throw SeatAlreadyTakenException(request.seatId)
        }

        seat.status = SeatStatus.HELD

        try {
            seatRepository.saveAndFlush(seat)
        } catch (ex: OptimisticLockingFailureException) {
            throw SeatAlreadyTakenException(request.seatId)
        }

        val reservation = reservationRepository.save(
            Reservation(
                userId = request.userId,
                eventId = request.eventId,
                seatId = request.seatId,
                status = ReservationStatus.PENDING,
                qrCode = generateQrCode(),
            )
        )

        return reservation.toResponse()
    }

    private fun generateQrCode(): String = "TT-" + UUID.randomUUID().toString().replace("-", "").take(20)
}

private fun Reservation.toResponse() = ReservationResponse(
    reservationId = requireNotNull(id),
    userId = userId,
    eventId = eventId,
    seatId = seatId,
    status = status,
    qrCode = qrCode,
    reservedAt = reservedAt,
)

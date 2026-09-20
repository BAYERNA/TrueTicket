package com.trueticket.ticket.service

import com.trueticket.ticket.domain.Reservation
import com.trueticket.ticket.domain.ReservationStatus
import com.trueticket.ticket.domain.SeatStatus
import com.trueticket.ticket.dto.AuthenticatedReservationRequest
import com.trueticket.ticket.dto.ReservationResponse
import com.trueticket.ticket.exception.SeatAlreadyTakenException
import com.trueticket.ticket.repository.ReservationRepository
import com.trueticket.ticket.repository.SeatRepository
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import org.springframework.beans.factory.annotation.Value
import java.time.Instant
import java.time.temporal.ChronoUnit
import java.util.UUID

/**
 * 좌석 선점 실패(Optimistic Lock)나 멱등성 키 충돌(UNIQUE 제약)은 트랜잭션을
 * rollback-only로 만든다. 같은 트랜잭션 안에서 예외를 잡고 "정상 반환"하면
 * Spring이 커밋 시점에 UnexpectedRollbackException을 던진다 — 실패한 쓰기
 * 트랜잭션을 별도 빈으로 분리해, 예외가 프록시 경계를 정상적으로 빠져나가
 * 트랜잭션이 깔끔하게 롤백되도록 한다. 실패 이후의 "재조회" 판단은
 * ReservationService가 완전히 새로운(별개) 트랜잭션에서 수행한다.
 */
@Service
class ReservationWriter(
    private val seatRepository: SeatRepository,
    private val reservationRepository: ReservationRepository,
    @Value("\${reservation.hold-minutes:5}") private val holdMinutes: Long,
) {

    fun findExisting(reservationSessionId: UUID): ReservationResponse? =
        reservationRepository.findByReservationSessionId(reservationSessionId)?.toResponse()

    /**
     * READ COMMITTED 격리 수준에서는 방금 커밋된 다른 트랜잭션의 행도 재조회 시점에는
     * 보일 수 있다. 동시에 같은 세션으로 두 번 들어온 요청 중 진 쪽이, 이긴 쪽의
     * 커밋을 기다릴 시간을 벌어주기 위해 짧게 몇 차례 재조회한다.
     */
    fun findExistingWithRetry(reservationSessionId: UUID): ReservationResponse? {
        repeat(3) { attempt ->
            findExisting(reservationSessionId)?.let { return it }
            if (attempt < 2) Thread.sleep(30)
        }
        return null
    }

    @Transactional
    fun holdSeatAndCreateReservation(request: AuthenticatedReservationRequest): ReservationResponse {
        val seat = seatRepository.findById(request.seatId)
            .orElseThrow { SeatAlreadyTakenException(request.seatId) }

        if (seat.status != SeatStatus.AVAILABLE) {
            throw SeatAlreadyTakenException(request.seatId)
        }

        seat.status = SeatStatus.HELD
        seatRepository.saveAndFlush(seat)

        return reservationRepository.saveAndFlush(
            Reservation(
                userId = request.userId,
                eventId = request.eventId,
                seatId = request.seatId,
                reservationSessionId = request.reservationSessionId,
                status = ReservationStatus.PENDING,
                qrCode = null,
                expiresAt = Instant.now().plus(holdMinutes, ChronoUnit.MINUTES),
            )
        ).toResponse()
    }
}

private fun Reservation.toResponse() = ReservationResponse(
    reservationId = requireNotNull(id),
    userId = userId,
    eventId = eventId,
    seatId = seatId,
    status = status,
    qrCode = qrCode,
    reservedAt = reservedAt,
    expiresAt = expiresAt,
)

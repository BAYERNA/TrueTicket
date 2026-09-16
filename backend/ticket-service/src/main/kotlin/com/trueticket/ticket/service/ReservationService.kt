package com.trueticket.ticket.service

import com.trueticket.ticket.client.BehaviorScoreRequest
import com.trueticket.ticket.client.BehaviorScoreResponse
import com.trueticket.ticket.client.BotDetectionClient
import com.trueticket.ticket.domain.Reservation
import com.trueticket.ticket.domain.ReservationStatus
import com.trueticket.ticket.domain.SeatStatus
import com.trueticket.ticket.dto.CreateReservationRequest
import com.trueticket.ticket.dto.ReservationResponse
import com.trueticket.ticket.exception.BotSuspectedException
import com.trueticket.ticket.exception.SeatAlreadyTakenException
import com.trueticket.ticket.repository.ReservationRepository
import com.trueticket.ticket.repository.SeatRepository
import org.slf4j.LoggerFactory
import org.springframework.cloud.client.circuitbreaker.CircuitBreakerFactory
import org.springframework.dao.OptimisticLockingFailureException
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.util.UUID

@Service
class ReservationService(
    private val seatRepository: SeatRepository,
    private val reservationRepository: ReservationRepository,
    private val botDetectionClient: BotDetectionClient,
    circuitBreakerFactory: CircuitBreakerFactory<*, *>,
) {
    private val log = LoggerFactory.getLogger(javaClass)
    private val botDetectionCircuitBreaker = circuitBreakerFactory.create("bot-detection-service")

    /**
     * FR-002-1: 좌석은 @Version 기반 Optimistic Lock으로 보호된다. 두 트랜잭션이
     * 동시에 같은 좌석을 읽고 저장하려 하면, 나중에 flush 되는 트랜잭션이
     * OptimisticLockingFailureException을 받는다. 여기서는 재시도 없이 즉시
     * "이미 선점된 좌석"으로 응답하여 사용자에게 다른 좌석을 고르도록 안내한다.
     */
    @Transactional
    fun reserve(request: CreateReservationRequest): ReservationResponse {
        checkAcquisitionScore(request.reservationSessionId)

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

    /**
     * bot-detection-service를 동기 호출(Orchestration)해 취득 부정성 스코어를 확인한다.
     * Circuit Breaker가 열려 있거나(장애 반복) 호출 자체가 실패하면, 예매 가용성을
     * 우선해 봇 탐지를 건너뛰고 통과시킨다 — 오탐 방지보다 서비스 중단이 더 큰 비용이다.
     */
    private fun checkAcquisitionScore(reservationSessionId: UUID) {
        val score = botDetectionCircuitBreaker.run(
            { botDetectionClient.getScore(BehaviorScoreRequest(reservationSessionId, "RESERVE_ATTEMPT")) },
            { ex: Throwable ->
                log.warn("bot-detection-service 호출 실패, 스코어 검사를 건너뜁니다: {}", ex.message)
                BehaviorScoreResponse(acquisitionFraudScore = 0.0, isFlagged = false)
            },
        )

        if (score.isFlagged) {
            throw BotSuspectedException(reservationSessionId)
        }
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
)

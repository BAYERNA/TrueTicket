package com.trueticket.ticket.service

import com.trueticket.ticket.client.BehaviorScoreRequest
import com.trueticket.ticket.client.BehaviorScoreResponse
import com.trueticket.ticket.client.BotDetectionClient
import com.trueticket.ticket.dto.AuthenticatedReservationRequest
import com.trueticket.ticket.dto.ReservationResponse
import com.trueticket.ticket.exception.BotSuspectedException
import com.trueticket.ticket.exception.SeatAlreadyTakenException
import com.trueticket.ticket.domain.PaymentStatus
import com.trueticket.ticket.domain.ReservationStatus
import com.trueticket.ticket.domain.SeatStatus
import com.trueticket.ticket.exception.ReservationAccessException
import com.trueticket.ticket.repository.PaymentRepository
import com.trueticket.ticket.repository.ReservationRepository
import com.trueticket.ticket.repository.SeatRepository
import org.slf4j.LoggerFactory
import org.springframework.cloud.client.circuitbreaker.CircuitBreakerFactory
import org.springframework.dao.DataIntegrityViolationException
import org.springframework.dao.OptimisticLockingFailureException
import org.springframework.stereotype.Service
import java.util.UUID
import java.time.Instant
import org.springframework.transaction.annotation.Transactional

@Service
class ReservationService(
    private val reservationWriter: ReservationWriter,
    private val botDetectionClient: BotDetectionClient,
    private val reservationRepository: ReservationRepository,
    private val seatRepository: SeatRepository,
    private val paymentRepository: PaymentRepository,
    circuitBreakerFactory: CircuitBreakerFactory<*, *>,
) {
    private val log = LoggerFactory.getLogger(javaClass)
    private val botDetectionCircuitBreaker = circuitBreakerFactory.create("bot-detection-service")

    /**
     * FR-002-1: 좌석은 @Version 기반 Optimistic Lock으로 보호된다. 실제 DB 쓰기는
     * ReservationWriter(별도 빈)에 위임한다 — 실패 시 그 트랜잭션이 정상적으로
     * 롤백되도록 예외가 프록시 경계를 빠져나가게 해야, 여기서 "재조회로 복구"를
     * 시도할 때 UnexpectedRollbackException 없이 새 트랜잭션을 열 수 있다.
     */
    fun reserve(request: AuthenticatedReservationRequest): ReservationResponse {
        reservationWriter.findExisting(request.reservationSessionId)?.let {
            log.info("중복 요청 감지, 기존 예매 건 반환: sessionId={}", request.reservationSessionId)
            return it
        }

        checkAcquisitionScore(request.reservationSessionId)

        return try {
            reservationWriter.holdSeatAndCreateReservation(request)
        } catch (ex: OptimisticLockingFailureException) {
            // 진짜 다른 사용자가 선점했을 수도 있지만, 같은 sessionId로 동시에 두 번
            // 호출된(더블클릭, 네트워크 재시도 등) 요청 중 진 쪽일 수도 있다.
            reservationWriter.findExistingWithRetry(request.reservationSessionId)
                ?: throw SeatAlreadyTakenException(request.seatId)
        } catch (ex: DataIntegrityViolationException) {
            // 위 findExisting과 holdSeatAndCreateReservation 사이에 동일 sessionId
            // 요청이 동시에 들어온 경합 상황. UNIQUE 제약이 막아준 뒤이므로, 그사이
            // 커밋된 기존 예매 건을 찾아 반환한다.
            reservationWriter.findExistingWithRetry(request.reservationSessionId) ?: throw ex
        }
    }

    @Transactional
    fun cancel(reservationId: UUID, userId: UUID): ReservationResponse {
        val reservation = reservationRepository.findByIdForUpdate(reservationId)
            ?: throw ReservationAccessException("예매를 찾을 수 없습니다.")
        if (reservation.userId != userId) throw ReservationAccessException("본인의 예매만 취소할 수 있습니다.")
        if (reservation.status == ReservationStatus.CANCELLED) return reservation.toResponse()

        val now = Instant.now()
        paymentRepository.findByReservationId(reservationId)?.let { payment ->
            if (payment.status == PaymentStatus.PAID) payment.status = PaymentStatus.REFUNDED
            if (payment.status == PaymentStatus.PENDING) payment.status = PaymentStatus.FAILED
            payment.updatedAt = now
            paymentRepository.save(payment)
        }
        seatRepository.findById(reservation.seatId).ifPresent { seat ->
            seat.status = SeatStatus.AVAILABLE
            seatRepository.save(seat)
        }
        reservation.status = ReservationStatus.CANCELLED
        reservation.cancelledAt = now
        reservation.qrCode = null
        return reservationRepository.save(reservation).toResponse()
    }

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

private fun com.trueticket.ticket.domain.Reservation.toResponse() = ReservationResponse(
    reservationId = requireNotNull(id),
    userId = userId,
    eventId = eventId,
    seatId = seatId,
    status = status,
    qrCode = qrCode,
    reservedAt = reservedAt,
    expiresAt = expiresAt,
)

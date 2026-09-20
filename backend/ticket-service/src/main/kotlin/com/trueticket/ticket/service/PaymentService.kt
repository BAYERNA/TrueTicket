package com.trueticket.ticket.service

import com.trueticket.ticket.domain.*
import com.trueticket.ticket.dto.*
import com.trueticket.ticket.exception.InvalidPaymentStateException
import com.trueticket.ticket.exception.PaymentNotFoundException
import com.trueticket.ticket.exception.ReservationAccessException
import com.trueticket.ticket.repository.PaymentRepository
import com.trueticket.ticket.repository.ReservationRepository
import com.trueticket.ticket.repository.SeatRepository
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.Instant
import java.util.UUID

@Service
class PaymentService(
    private val paymentRepository: PaymentRepository,
    private val reservationRepository: ReservationRepository,
    private val seatRepository: SeatRepository,
) {
    @Transactional
    fun prepare(reservationId: UUID, userId: UUID, request: PreparePaymentRequest): PaymentResponse {
        paymentRepository.findByIdempotencyKey(request.idempotencyKey)?.let { existing ->
            if (existing.reservationId != reservationId) {
                throw InvalidPaymentStateException("이미 다른 결제에 사용된 멱등성 키입니다.")
            }
            val reservation = reservationRepository.findById(existing.reservationId)
                .orElseThrow { ReservationAccessException("예매를 찾을 수 없습니다.") }
            if (reservation.userId != userId) throw ReservationAccessException("본인의 결제만 조회할 수 있습니다.")
            return existing.toResponse(reservation.expiresAt)
        }

        val reservation = reservationRepository.findByIdForUpdate(reservationId)
            ?: throw ReservationAccessException("예매를 찾을 수 없습니다.")
        if (reservation.userId != userId) throw ReservationAccessException("본인의 예매만 결제할 수 있습니다.")
        if (reservation.status != ReservationStatus.PENDING || reservation.expiresAt <= Instant.now()) {
            throw InvalidPaymentStateException("결제 가능한 예매가 아니거나 좌석 선점 시간이 만료되었습니다.")
        }
        paymentRepository.findByReservationId(reservationId)?.let { return it.toResponse(reservation.expiresAt) }
        val seat = seatRepository.findById(reservation.seatId)
            .orElseThrow { InvalidPaymentStateException("좌석을 찾을 수 없습니다.") }
        val payment = paymentRepository.save(
            Payment(
                reservationId = reservationId,
                amount = seat.price,
                paymentMethod = request.paymentMethod,
                idempotencyKey = request.idempotencyKey,
                providerPaymentId = "mock_${UUID.randomUUID().toString().replace("-", "")}",
            )
        )
        return payment.toResponse(reservation.expiresAt)
    }

    @Transactional
    fun processMockWebhook(request: MockPaymentWebhookRequest): PaymentResponse {
        val payment = paymentRepository.findByProviderPaymentIdForUpdate(request.providerPaymentId)
            ?: throw PaymentNotFoundException()
        val reservation = reservationRepository.findByIdForUpdate(payment.reservationId)
            ?: throw ReservationAccessException("예매를 찾을 수 없습니다.")
        if (payment.webhookEventId == request.eventId) return payment.toResponse(reservation.expiresAt)
        if (payment.status != PaymentStatus.PENDING || reservation.status != ReservationStatus.PENDING) {
            throw InvalidPaymentStateException("이미 종료된 결제입니다.")
        }

        val now = Instant.now()
        payment.webhookEventId = request.eventId
        payment.updatedAt = now
        if (request.result == MockPaymentResult.PAID && reservation.expiresAt > now) {
            payment.status = PaymentStatus.PAID
            payment.paidAt = now
            reservation.status = ReservationStatus.CONFIRMED
            reservation.confirmedAt = now
            reservation.qrCode = generateQrCode()
            seatRepository.findById(reservation.seatId).ifPresent { seat ->
                seat.status = SeatStatus.SOLD
                seatRepository.save(seat)
            }
        } else {
            payment.status = PaymentStatus.FAILED
            payment.failureReason = request.failureReason ?: if (reservation.expiresAt <= now) "RESERVATION_EXPIRED" else "PAYMENT_FAILED"
            reservation.status = ReservationStatus.CANCELLED
            reservation.cancelledAt = now
            seatRepository.findById(reservation.seatId).ifPresent { seat ->
                seat.status = SeatStatus.AVAILABLE
                seatRepository.save(seat)
            }
        }
        paymentRepository.save(payment)
        reservationRepository.save(reservation)
        return payment.toResponse(reservation.expiresAt)
    }

    @Transactional
    fun completeMockPayment(paymentId: UUID, userId: UUID): PaymentResponse {
        val payment = paymentRepository.findById(paymentId).orElseThrow { PaymentNotFoundException() }
        val reservation = reservationRepository.findById(payment.reservationId)
            .orElseThrow { ReservationAccessException("예매를 찾을 수 없습니다.") }
        if (reservation.userId != userId) throw ReservationAccessException("본인의 결제만 완료할 수 있습니다.")
        return processMockWebhook(
            MockPaymentWebhookRequest(
                eventId = "demo_${UUID.randomUUID()}",
                providerPaymentId = payment.providerPaymentId,
                result = MockPaymentResult.PAID,
            )
        )
    }

    private fun generateQrCode(): String = "TT-" + UUID.randomUUID().toString().replace("-", "").take(20)
}

private fun Payment.toResponse(expiresAt: Instant) = PaymentResponse(
    paymentId = requireNotNull(id),
    reservationId = reservationId,
    providerPaymentId = providerPaymentId,
    amount = amount,
    status = status,
    reservationExpiresAt = expiresAt,
    mockCheckoutToken = providerPaymentId,
)

package com.trueticket.ticket.service

import com.trueticket.ticket.domain.*
import com.trueticket.ticket.dto.MockPaymentResult
import com.trueticket.ticket.dto.MockPaymentWebhookRequest
import com.trueticket.ticket.dto.PreparePaymentRequest
import com.trueticket.ticket.repository.PaymentRepository
import com.trueticket.ticket.repository.ReservationRepository
import com.trueticket.ticket.repository.SeatRepository
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import java.math.BigDecimal
import java.time.Instant
import java.time.temporal.ChronoUnit
import java.util.Optional
import java.util.UUID

class PaymentServiceTest {
    private val paymentRepository = mockk<PaymentRepository>()
    private val reservationRepository = mockk<ReservationRepository>()
    private val seatRepository = mockk<SeatRepository>()
    private val service = PaymentService(paymentRepository, reservationRepository, seatRepository)

    @Test
    fun `successful webhook confirms reservation, sells seat, and issues QR`() {
        val reservationId = UUID.randomUUID()
        val seatId = UUID.randomUUID()
        val paymentId = UUID.randomUUID()
        val reservation = reservation(reservationId, seatId)
        val seat = seat(seatId)
        val payment = payment(paymentId, reservationId)
        every { paymentRepository.findByProviderPaymentIdForUpdate("mock_provider") } returns payment
        every { reservationRepository.findByIdForUpdate(reservationId) } returns reservation
        every { seatRepository.findById(seatId) } returns Optional.of(seat)
        every { seatRepository.save(any()) } answers { firstArg() }
        every { paymentRepository.save(any()) } answers { firstArg() }
        every { reservationRepository.save(any()) } answers { firstArg() }

        val response = service.processMockWebhook(
            MockPaymentWebhookRequest("evt-1", "mock_provider", MockPaymentResult.PAID)
        )

        assertThat(response.status).isEqualTo(PaymentStatus.PAID)
        assertThat(reservation.status).isEqualTo(ReservationStatus.CONFIRMED)
        assertThat(reservation.qrCode).startsWith("TT-")
        assertThat(seat.status).isEqualTo(SeatStatus.SOLD)
    }

    @Test
    fun `same webhook event is idempotent`() {
        val reservationId = UUID.randomUUID()
        val payment = payment(UUID.randomUUID(), reservationId).apply { webhookEventId = "evt-1" }
        val reservation = reservation(reservationId, UUID.randomUUID())
        every { paymentRepository.findByProviderPaymentIdForUpdate("mock_provider") } returns payment
        every { reservationRepository.findByIdForUpdate(reservationId) } returns reservation

        service.processMockWebhook(MockPaymentWebhookRequest("evt-1", "mock_provider", MockPaymentResult.PAID))

        verify(exactly = 0) { paymentRepository.save(any()) }
        verify(exactly = 0) { reservationRepository.save(any()) }
    }

    @Test
    fun `prepare returns existing payment for repeated idempotency key`() {
        val userId = UUID.randomUUID()
        val reservationId = UUID.randomUUID()
        val key = UUID.randomUUID()
        val reservation = reservation(reservationId, UUID.randomUUID(), userId)
        val payment = payment(UUID.randomUUID(), reservationId, key)
        every { paymentRepository.findByIdempotencyKey(key) } returns payment
        every { reservationRepository.findById(reservationId) } returns Optional.of(reservation)

        val response = service.prepare(reservationId, userId, PreparePaymentRequest(key, "CARD"))

        assertThat(response.paymentId).isEqualTo(payment.id)
        verify(exactly = 0) { paymentRepository.save(any()) }
    }

    private fun reservation(
        id: UUID,
        seatId: UUID,
        userId: UUID = UUID.randomUUID(),
    ) = Reservation(
        id = id,
        userId = userId,
        eventId = UUID.randomUUID(),
        seatId = seatId,
        expiresAt = Instant.now().plus(5, ChronoUnit.MINUTES),
    )

    private fun seat(id: UUID) = Seat(
        id = id,
        eventId = UUID.randomUUID(),
        seatSection = "A",
        seatRow = "1",
        seatNumber = 1,
        price = BigDecimal("50000"),
        status = SeatStatus.HELD,
    )

    private fun payment(
        id: UUID,
        reservationId: UUID,
        idempotencyKey: UUID = UUID.randomUUID(),
    ) = Payment(
        id = id,
        reservationId = reservationId,
        amount = BigDecimal("50000"),
        idempotencyKey = idempotencyKey,
        providerPaymentId = "mock_provider",
    )
}

package com.trueticket.ticket.dto

import com.trueticket.ticket.domain.PaymentStatus
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.NotNull
import java.math.BigDecimal
import java.time.Instant
import java.util.UUID

data class PreparePaymentRequest(
    @field:NotNull val idempotencyKey: UUID,
    @field:NotBlank val paymentMethod: String,
)

data class PaymentResponse(
    val paymentId: UUID,
    val reservationId: UUID,
    val providerPaymentId: String,
    val amount: BigDecimal,
    val status: PaymentStatus,
    val reservationExpiresAt: Instant,
    val mockCheckoutToken: String,
)

enum class MockPaymentResult { PAID, FAILED }

data class MockPaymentWebhookRequest(
    @field:NotBlank val eventId: String,
    @field:NotBlank val providerPaymentId: String,
    @field:NotNull val result: MockPaymentResult,
    val failureReason: String? = null,
)

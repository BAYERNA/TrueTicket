package com.trueticket.ticket.controller

import com.trueticket.ticket.dto.MockPaymentWebhookRequest
import com.trueticket.ticket.dto.PaymentResponse
import com.trueticket.ticket.dto.PreparePaymentRequest
import com.trueticket.ticket.service.PaymentService
import jakarta.validation.Valid
import org.springframework.beans.factory.annotation.Value
import org.springframework.http.HttpStatus
import org.springframework.security.core.annotation.AuthenticationPrincipal
import org.springframework.security.oauth2.jwt.Jwt
import org.springframework.web.bind.annotation.*
import org.springframework.web.server.ResponseStatusException
import java.util.UUID

@RestController
@RequestMapping("/api/payments")
class PaymentController(
    private val paymentService: PaymentService,
    @Value("\${security.payment-webhook-secret}") private val webhookSecret: String,
    @Value("\${payment.mock-enabled:false}") private val mockEnabled: Boolean,
) {
    @PostMapping("/{reservationId}/prepare")
    fun prepare(
        @AuthenticationPrincipal jwt: Jwt,
        @PathVariable reservationId: UUID,
        @Valid @RequestBody request: PreparePaymentRequest,
    ): PaymentResponse = paymentService.prepare(reservationId, UUID.fromString(jwt.subject), request)

    @PostMapping("/webhooks/mock")
    fun mockWebhook(
        @RequestHeader("X-Payment-Webhook-Secret", required = false) secret: String?,
        @Valid @RequestBody request: MockPaymentWebhookRequest,
    ): PaymentResponse {
        if (secret != webhookSecret) throw ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid webhook secret")
        return paymentService.processMockWebhook(request)
    }

    @PostMapping("/{paymentId}/mock-complete")
    fun mockComplete(
        @AuthenticationPrincipal jwt: Jwt,
        @PathVariable paymentId: UUID,
    ): PaymentResponse {
        if (!mockEnabled) throw ResponseStatusException(HttpStatus.NOT_FOUND)
        return paymentService.completeMockPayment(paymentId, UUID.fromString(jwt.subject))
    }
}

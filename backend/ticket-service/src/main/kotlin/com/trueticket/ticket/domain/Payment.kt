package com.trueticket.ticket.domain

import jakarta.persistence.*
import java.math.BigDecimal
import java.time.Instant
import java.util.UUID

enum class PaymentStatus { PENDING, PAID, FAILED, REFUNDED }

@Entity
@Table(name = "payments")
class Payment(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "payment_id")
    val id: UUID? = null,

    @Column(name = "reservation_id", nullable = false, unique = true)
    var reservationId: UUID,

    @Column(nullable = false)
    var amount: BigDecimal,

    @Column(name = "payment_method")
    var paymentMethod: String? = null,

    @Enumerated(EnumType.STRING)
    @Column(name = "payment_status", nullable = false)
    var status: PaymentStatus = PaymentStatus.PENDING,

    @Column(name = "paid_at")
    var paidAt: Instant? = null,

    @Column(name = "idempotency_key", nullable = false, unique = true)
    var idempotencyKey: UUID,

    @Column(name = "provider_payment_id", nullable = false, unique = true)
    var providerPaymentId: String,

    @Column(name = "webhook_event_id", unique = true)
    var webhookEventId: String? = null,

    @Column(name = "failure_reason")
    var failureReason: String? = null,

    @Column(name = "created_at", nullable = false, updatable = false)
    val createdAt: Instant = Instant.now(),

    @Column(name = "updated_at", nullable = false)
    var updatedAt: Instant = Instant.now(),
)

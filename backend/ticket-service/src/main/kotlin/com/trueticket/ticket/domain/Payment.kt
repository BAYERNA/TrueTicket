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
)

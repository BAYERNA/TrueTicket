package com.trueticket.ticket.domain

import jakarta.persistence.*
import java.time.Instant
import java.util.UUID

enum class ReservationStatus { PENDING, CONFIRMED, CANCELLED }

@Entity
@Table(name = "reservations")
class Reservation(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "reservation_id")
    val id: UUID? = null,

    @Column(name = "user_id", nullable = false)
    var userId: UUID,

    @Column(name = "event_id", nullable = false)
    var eventId: UUID,

    @Column(name = "seat_id", nullable = false)
    var seatId: UUID,

    @Column(name = "reservation_session_id", unique = true)
    var reservationSessionId: UUID? = null,

    @Enumerated(EnumType.STRING)
    @Column(name = "reservation_status", nullable = false)
    var status: ReservationStatus = ReservationStatus.PENDING,

    @Column(name = "qr_code", unique = true)
    var qrCode: String? = null,

    @Column(name = "reserved_at", nullable = false, updatable = false)
    val reservedAt: Instant = Instant.now(),

    @Column(name = "confirmed_at")
    var confirmedAt: Instant? = null,
)

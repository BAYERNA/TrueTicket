package com.trueticket.ticket.domain

import jakarta.persistence.*
import java.math.BigDecimal
import java.time.Instant
import java.util.UUID

enum class EventCategory { KBO, CONCERT, MUSICAL, ETC }

@Entity
@Table(name = "events")
class Event(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "event_id")
    val id: UUID? = null,

    var title: String,

    @Enumerated(EnumType.STRING)
    var category: EventCategory,

    var venue: String,

    @Column(name = "event_datetime", nullable = false)
    var eventDatetime: Instant,

    @Column(name = "base_price", nullable = false)
    var basePrice: BigDecimal,

    @Column(name = "created_at", nullable = false, updatable = false)
    val createdAt: Instant = Instant.now(),
)

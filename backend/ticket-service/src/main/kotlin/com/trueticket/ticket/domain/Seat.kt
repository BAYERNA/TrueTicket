package com.trueticket.ticket.domain

import jakarta.persistence.*
import java.math.BigDecimal
import java.util.UUID

enum class SeatStatus { AVAILABLE, HELD, RESERVED, SOLD }

/**
 * FR-002-1: 동시 요청 간 좌석 중복 선점을 방지하기 위해 JPA Optimistic Lock(@Version)을 사용한다.
 * 동시에 같은 좌석을 예매 요청하면 나중에 커밋하는 트랜잭션이 OptimisticLockException을 받고,
 * 서비스 계층에서 이를 "이미 선점된 좌석" 응답으로 변환한다.
 */
@Entity
@Table(name = "seats")
class Seat(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "seat_id")
    val id: UUID? = null,

    @Column(name = "event_id", nullable = false)
    var eventId: UUID,

    @Column(name = "seat_section", nullable = false)
    var seatSection: String,

    @Column(name = "seat_row", nullable = false)
    var seatRow: String,

    @Column(name = "seat_number", nullable = false)
    var seatNumber: Int,

    @Column(nullable = false)
    var price: BigDecimal,

    @Enumerated(EnumType.STRING)
    var status: SeatStatus = SeatStatus.AVAILABLE,

    @Version
    var version: Long = 0,
)

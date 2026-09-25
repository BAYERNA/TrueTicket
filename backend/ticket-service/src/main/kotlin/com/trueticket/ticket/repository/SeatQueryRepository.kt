package com.trueticket.ticket.repository

import com.querydsl.core.BooleanBuilder
import com.querydsl.jpa.impl.JPAQueryFactory
import com.trueticket.ticket.domain.QSeat.seat
import com.trueticket.ticket.domain.Seat
import com.trueticket.ticket.domain.SeatStatus
import org.springframework.stereotype.Repository
import java.math.BigDecimal
import java.util.UUID

/**
 * 좌석 검색은 구역/상태/가격대 조합이 요청마다 달라진다 — 조건마다 별도의
 * findByXxx 메서드를 만드는 대신 QueryDSL로 필요한 조건만 동적으로 조립한다.
 */
@Repository
class SeatQueryRepository(private val queryFactory: JPAQueryFactory) {

    fun search(
        eventId: UUID,
        section: String?,
        status: SeatStatus?,
        minPrice: BigDecimal?,
        maxPrice: BigDecimal?,
    ): List<Seat> {
        val where = BooleanBuilder()
        where.and(seat.eventId.eq(eventId))
        section?.let { where.and(seat.seatSection.eq(it)) }
        status?.let { where.and(seat.status.eq(it)) }
        minPrice?.let { where.and(seat.price.goe(it)) }
        maxPrice?.let { where.and(seat.price.loe(it)) }

        return queryFactory
            .selectFrom(seat)
            .where(where)
            .orderBy(seat.seatSection.asc(), seat.seatRow.asc(), seat.seatNumber.asc())
            .fetch()
    }
}

package com.trueticket.ticket.controller

import com.trueticket.ticket.domain.Event
import com.trueticket.ticket.domain.Seat
import com.trueticket.ticket.domain.SeatStatus
import com.trueticket.ticket.repository.EventRepository
import com.trueticket.ticket.repository.SeatQueryRepository
import com.trueticket.ticket.repository.SeatRepository
import org.springframework.web.bind.annotation.*
import java.math.BigDecimal
import java.util.UUID

@RestController
@RequestMapping("/api/events")
class EventController(
    private val eventRepository: EventRepository,
    private val seatRepository: SeatRepository,
    private val seatQueryRepository: SeatQueryRepository,
) {

    @GetMapping
    fun listEvents(): List<Event> = eventRepository.findAll()

    @GetMapping("/{eventId}/seats")
    fun listAvailableSeats(@PathVariable eventId: UUID): List<Seat> =
        seatRepository.findByEventIdAndStatus(eventId, SeatStatus.AVAILABLE)

    /** 구역/상태/가격대를 필요한 조합만 골라 좁혀나가는 동적 좌석 검색(QueryDSL). */
    @GetMapping("/{eventId}/seats/search")
    fun searchSeats(
        @PathVariable eventId: UUID,
        @RequestParam(required = false) section: String?,
        @RequestParam(required = false) status: SeatStatus?,
        @RequestParam(required = false) minPrice: BigDecimal?,
        @RequestParam(required = false) maxPrice: BigDecimal?,
    ): List<Seat> = seatQueryRepository.search(eventId, section, status, minPrice, maxPrice)
}

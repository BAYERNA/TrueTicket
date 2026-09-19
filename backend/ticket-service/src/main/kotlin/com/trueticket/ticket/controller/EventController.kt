package com.trueticket.ticket.controller

import com.trueticket.ticket.domain.Event
import com.trueticket.ticket.domain.Seat
import com.trueticket.ticket.domain.SeatStatus
import com.trueticket.ticket.repository.EventRepository
import com.trueticket.ticket.repository.SeatRepository
import org.springframework.web.bind.annotation.*
import java.util.UUID

@RestController
@RequestMapping("/api/events")
class EventController(
    private val eventRepository: EventRepository,
    private val seatRepository: SeatRepository,
) {

    @GetMapping
    fun listEvents(): List<Event> = eventRepository.findAll()

    @GetMapping("/{eventId}/seats")
    fun listAvailableSeats(@PathVariable eventId: UUID): List<Seat> =
        seatRepository.findByEventIdAndStatus(eventId, SeatStatus.AVAILABLE)
}

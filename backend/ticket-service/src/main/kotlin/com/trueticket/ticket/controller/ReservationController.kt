package com.trueticket.ticket.controller

import com.trueticket.ticket.domain.Reservation
import com.trueticket.ticket.dto.CreateReservationRequest
import com.trueticket.ticket.dto.ReservationResponse
import com.trueticket.ticket.exception.SeatAlreadyTakenException
import com.trueticket.ticket.repository.ReservationRepository
import com.trueticket.ticket.service.ReservationService
import jakarta.validation.Valid
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*
import java.util.UUID

@RestController
@RequestMapping("/api/reservations")
class ReservationController(
    private val reservationService: ReservationService,
    private val reservationRepository: ReservationRepository,
) {

    @PostMapping
    fun reserve(@Valid @RequestBody request: CreateReservationRequest): ResponseEntity<ReservationResponse> =
        ResponseEntity.status(HttpStatus.CREATED).body(reservationService.reserve(request))

    /** SCR-05 마이 티켓: 사용자의 예매 내역 목록. */
    @GetMapping
    fun findByUser(@RequestParam userId: UUID): List<ReservationResponse> =
        reservationRepository.findByUserId(userId).map { it.toResponse() }

    /** FR-010: 현장 검표 시 verification-service가 QR 코드로 예매 건을 조회하기 위한 조회 전용 엔드포인트. */
    @GetMapping("/qr/{qrCode}")
    fun findByQrCode(@PathVariable qrCode: String): ResponseEntity<ReservationResponse> {
        val reservation = reservationRepository.findByQrCode(qrCode) ?: return ResponseEntity.notFound().build()
        return ResponseEntity.ok(reservation.toResponse())
    }

    @ExceptionHandler(SeatAlreadyTakenException::class)
    fun handleSeatAlreadyTaken(ex: SeatAlreadyTakenException): ResponseEntity<Map<String, String>> =
        ResponseEntity.status(HttpStatus.CONFLICT).body(mapOf("message" to (ex.message ?: "Seat already taken")))
}

private fun Reservation.toResponse() = ReservationResponse(
    reservationId = requireNotNull(id),
    userId = userId,
    eventId = eventId,
    seatId = seatId,
    status = status,
    qrCode = qrCode,
    reservedAt = reservedAt,
)

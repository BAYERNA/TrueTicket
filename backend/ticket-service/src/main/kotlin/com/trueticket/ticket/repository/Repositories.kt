package com.trueticket.ticket.repository

import com.trueticket.ticket.domain.*
import org.springframework.data.jpa.repository.JpaRepository
import java.util.UUID

interface UserRepository : JpaRepository<User, UUID> {
    fun findByEmail(email: String): User?
}

interface EventRepository : JpaRepository<Event, UUID>

interface SeatRepository : JpaRepository<Seat, UUID> {
    fun findByEventIdAndStatus(eventId: UUID, status: SeatStatus): List<Seat>
}

interface ReservationRepository : JpaRepository<Reservation, UUID> {
    fun findByUserId(userId: UUID): List<Reservation>
    fun findByUserIdAndEventId(userId: UUID, eventId: UUID): List<Reservation>
    fun findByQrCode(qrCode: String): Reservation?
    fun findByReservationSessionId(reservationSessionId: UUID): Reservation?
}

interface PaymentRepository : JpaRepository<Payment, UUID> {
    fun findByReservationId(reservationId: UUID): Payment?
}

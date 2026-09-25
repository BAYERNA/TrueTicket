package com.trueticket.ticket.repository

import com.trueticket.ticket.domain.*
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Lock
import org.springframework.data.jpa.repository.Query
import jakarta.persistence.LockModeType
import java.time.Instant
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
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    fun findByStatusAndExpiresAtBefore(status: ReservationStatus, expiresAt: Instant): List<Reservation>

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select r from Reservation r where r.id = :id")
    fun findByIdForUpdate(id: UUID): Reservation?
}

interface PaymentRepository : JpaRepository<Payment, UUID> {
    fun findByReservationId(reservationId: UUID): Payment?
    fun findByIdempotencyKey(idempotencyKey: UUID): Payment?
    fun findByProviderPaymentId(providerPaymentId: String): Payment?

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select p from Payment p where p.providerPaymentId = :providerPaymentId")
    fun findByProviderPaymentIdForUpdate(providerPaymentId: String): Payment?
}

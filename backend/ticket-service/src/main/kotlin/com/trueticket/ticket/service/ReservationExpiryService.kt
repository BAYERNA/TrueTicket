package com.trueticket.ticket.service

import com.trueticket.ticket.domain.PaymentStatus
import com.trueticket.ticket.domain.ReservationStatus
import com.trueticket.ticket.domain.SeatStatus
import com.trueticket.ticket.repository.PaymentRepository
import com.trueticket.ticket.repository.ReservationRepository
import com.trueticket.ticket.repository.SeatRepository
import org.springframework.scheduling.annotation.Scheduled
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.Instant

@Service
class ReservationExpiryService(
    private val reservationRepository: ReservationRepository,
    private val paymentRepository: PaymentRepository,
    private val seatRepository: SeatRepository,
) {
    @Scheduled(fixedDelayString = "\${reservation.expiry-scan-ms:30000}")
    @Transactional
    fun releaseExpiredHolds() {
        val now = Instant.now()
        reservationRepository.findByStatusAndExpiresAtBefore(ReservationStatus.PENDING, now).forEach { reservation ->
            reservation.status = ReservationStatus.CANCELLED
            reservation.cancelledAt = now
            paymentRepository.findByReservationId(requireNotNull(reservation.id))?.let { payment ->
                if (payment.status == PaymentStatus.PENDING) {
                    payment.status = PaymentStatus.FAILED
                    payment.failureReason = "RESERVATION_EXPIRED"
                    payment.updatedAt = now
                    paymentRepository.save(payment)
                }
            }
            seatRepository.findById(reservation.seatId).ifPresent { seat ->
                if (seat.status == SeatStatus.HELD) {
                    seat.status = SeatStatus.AVAILABLE
                    seatRepository.save(seat)
                }
            }
            reservationRepository.save(reservation)
        }
    }
}

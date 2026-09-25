package com.trueticket.ticket.exception

class ReservationAccessException(message: String) : RuntimeException(message)
class InvalidPaymentStateException(message: String) : RuntimeException(message)
class PaymentNotFoundException : RuntimeException("결제 건을 찾을 수 없습니다.")

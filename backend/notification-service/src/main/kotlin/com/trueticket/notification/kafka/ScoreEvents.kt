package com.trueticket.notification.kafka

import java.time.Instant
import java.util.UUID

/** bot-detection-service가 예매 세션 단위로 발행하는 취득 부정성 스코어 이벤트. */
data class AcquisitionScoreEvent(
    val reservationSessionId: UUID,
    val acquisitionFraudScore: Double,
    val isFlagged: Boolean,
    val evaluatedAt: Instant,
)

/**
 * resale-monitor-service가 재판매 게시물 단위로 발행하는 상습 판매 스코어 이벤트.
 * 크롤링한 게시물이 특정 예매 세션(원 구매 건)과 매칭되는 경우에만 reservationSessionId가 채워진다.
 */
data class HabitualScoreEvent(
    val reservationSessionId: UUID,
    val listingId: UUID,
    val habitualScore: Double,
    val isFlagged: Boolean,
    val evaluatedAt: Instant,
)

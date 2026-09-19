package com.trueticket.notification.domain

import jakarta.persistence.*
import java.time.Instant
import java.util.UUID

/**
 * bot-detection-service와 resale-monitor-service는 서로 다른 시점에 독립적으로
 * Kafka 이벤트를 발행한다(Choreography). 두 스코어가 모두 도착하기 전까지 이 테이블에
 * 부분 상태로 보관하고, AND 조건을 평가할 때마다 갱신한다. 판정이 완료되면(scam_judgments
 * 저장) 이 레코드는 삭제한다.
 */
@Entity
@Table(name = "pending_score_joins")
class PendingScoreJoin(
    @Id
    @Column(name = "reservation_session_id")
    val reservationSessionId: UUID,

    @Column(name = "listing_id")
    var listingId: UUID? = null,

    @Column(name = "acquisition_score")
    var acquisitionScore: Double? = null,

    @Column(name = "habitual_score")
    var habitualScore: Double? = null,

    @Column(name = "updated_at", nullable = false)
    var updatedAt: Instant = Instant.now(),
) {
    fun isReadyToJudge(): Boolean = acquisitionScore != null && habitualScore != null
}

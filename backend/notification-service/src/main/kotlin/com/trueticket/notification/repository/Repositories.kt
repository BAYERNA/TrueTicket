package com.trueticket.notification.repository

import com.trueticket.notification.domain.Notification
import com.trueticket.notification.domain.PendingScoreJoin
import com.trueticket.notification.domain.Report
import com.trueticket.notification.domain.ScamJudgment
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Modifying
import org.springframework.data.jpa.repository.Query
import org.springframework.data.repository.query.Param
import java.time.Instant
import java.util.UUID

interface ScamJudgmentRepository : JpaRepository<ScamJudgment, UUID> {
    fun findByReservationSessionId(reservationSessionId: UUID): List<ScamJudgment>

    /**
     * Kafka는 at-least-once 전달이므로 같은 이벤트가 다시 도착할 수 있다. DB의 유니크
     * 인덱스와 ON CONFLICT를 함께 사용해 판정 저장을 원자적으로 멱등 처리한다.
     */
    @Modifying
    @Query(
        value = """
            INSERT INTO scam_judgments (
                judgment_id, reservation_session_id, listing_id,
                acquisition_score, habitual_score, verdict, judged_at
            ) VALUES (
                :judgmentId, :reservationSessionId, :listingId,
                :acquisitionScore, :habitualScore, :verdict, :judgedAt
            )
            ON CONFLICT (reservation_session_id, listing_id) DO NOTHING
        """,
        nativeQuery = true,
    )
    fun insertIfAbsent(
        @Param("judgmentId") judgmentId: UUID,
        @Param("reservationSessionId") reservationSessionId: UUID,
        @Param("listingId") listingId: UUID,
        @Param("acquisitionScore") acquisitionScore: Double,
        @Param("habitualScore") habitualScore: Double,
        @Param("verdict") verdict: String,
        @Param("judgedAt") judgedAt: Instant,
    ): Int
}

interface PendingScoreJoinRepository : JpaRepository<PendingScoreJoin, UUID> {
    fun deleteByUpdatedAtBefore(cutoff: Instant): Long
}

interface ReportRepository : JpaRepository<Report, UUID>

interface NotificationRepository : JpaRepository<Notification, UUID> {
    fun findByUserIdOrderByCreatedAtDesc(userId: UUID): List<Notification>
}

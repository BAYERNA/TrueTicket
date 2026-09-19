package com.trueticket.notification.repository

import com.trueticket.notification.domain.Notification
import com.trueticket.notification.domain.PendingScoreJoin
import com.trueticket.notification.domain.Report
import com.trueticket.notification.domain.ScamJudgment
import org.springframework.data.jpa.repository.JpaRepository
import java.util.UUID

interface ScamJudgmentRepository : JpaRepository<ScamJudgment, UUID> {
    fun findByReservationSessionId(reservationSessionId: UUID): List<ScamJudgment>
}

interface PendingScoreJoinRepository : JpaRepository<PendingScoreJoin, UUID>

interface ReportRepository : JpaRepository<Report, UUID>

interface NotificationRepository : JpaRepository<Notification, UUID> {
    fun findByUserIdOrderByCreatedAtDesc(userId: UUID): List<Notification>
}

package com.trueticket.notification.domain

import jakarta.persistence.*
import java.time.Instant
import java.util.UUID

enum class ReportStatus { RECEIVED, REVIEWING, RESOLVED, REJECTED }

@Entity
@Table(name = "reports")
class Report(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "report_id")
    val id: UUID? = null,

    @Column(name = "reporter_user_id", nullable = false)
    var reporterUserId: UUID,

    @Column(name = "target_listing_id")
    var targetListingId: UUID? = null,

    @Column(name = "report_reason", nullable = false)
    var reportReason: String,

    @Enumerated(EnumType.STRING)
    @Column(name = "report_status", nullable = false)
    var status: ReportStatus = ReportStatus.RECEIVED,

    @Column(name = "created_at", nullable = false, updatable = false)
    val createdAt: Instant = Instant.now(),
)

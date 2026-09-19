package com.trueticket.notification.domain

import jakarta.persistence.*
import java.time.Instant
import java.util.UUID

enum class NotificationType { JUDGMENT_RESULT, REPORT_RESULT, SYSTEM }

@Entity
@Table(name = "notifications")
class Notification(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "notification_id")
    val id: UUID? = null,

    @Column(name = "user_id", nullable = false)
    var userId: UUID,

    @Enumerated(EnumType.STRING)
    @Column(name = "notification_type", nullable = false)
    var type: NotificationType,

    @Column(nullable = false)
    var message: String,

    @Column(name = "is_read", nullable = false)
    var isRead: Boolean = false,

    @Column(name = "created_at", nullable = false, updatable = false)
    val createdAt: Instant = Instant.now(),
)

package com.trueticket.notification.controller

import com.trueticket.notification.domain.Notification
import com.trueticket.notification.repository.NotificationRepository
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController
import java.util.UUID

/** SCR-12: 판정 결과, 신고 처리 상태 등 개인화된 알림을 확인한다. */
@RestController
@RequestMapping("/api/notifications")
class NotificationController(
    private val notificationRepository: NotificationRepository,
) {

    @GetMapping
    fun findByUser(@RequestParam userId: UUID): List<Notification> =
        notificationRepository.findByUserIdOrderByCreatedAtDesc(userId)
}

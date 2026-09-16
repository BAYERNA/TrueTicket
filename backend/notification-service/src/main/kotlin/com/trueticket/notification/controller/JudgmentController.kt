package com.trueticket.notification.controller

import com.trueticket.notification.domain.ScamJudgment
import com.trueticket.notification.repository.ScamJudgmentRepository
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import java.util.UUID

@RestController
@RequestMapping("/api/judgments")
class JudgmentController(
    private val scamJudgmentRepository: ScamJudgmentRepository,
) {

    @GetMapping("/session/{reservationSessionId}")
    fun findBySession(@PathVariable reservationSessionId: UUID): List<ScamJudgment> =
        scamJudgmentRepository.findByReservationSessionId(reservationSessionId)
}

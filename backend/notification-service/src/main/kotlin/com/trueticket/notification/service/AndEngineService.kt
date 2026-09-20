package com.trueticket.notification.service

import com.trueticket.notification.domain.PendingScoreJoin
import com.trueticket.notification.domain.Verdict
import com.trueticket.notification.kafka.AcquisitionScoreEvent
import com.trueticket.notification.kafka.HabitualScoreEvent
import com.trueticket.notification.repository.PendingScoreJoinRepository
import com.trueticket.notification.repository.ScamJudgmentRepository
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.Instant
import java.util.UUID

/**
 * 3.2 기술적 판별 기준 / AND 엔진: 취득 부정성 스코어와 상습 판매 스코어가 각각
 * 독립적으로 도착하는 두 이벤트를 예매 세션(reservationSessionId) 기준으로 조인하고,
 * 두 스코어가 모두 임계치를 초과할 때만 SUSPECTED로 판정한다. 어느 한쪽만 초과하면
 * 선의의 이용자로 보아 CLEAR로 기록한다(NFR-007 오탐률 관리).
 */
@Service
class AndEngineService(
    private val pendingScoreJoinRepository: PendingScoreJoinRepository,
    private val scamJudgmentRepository: ScamJudgmentRepository,
    @Value("\${trueticket.and-engine.acquisition-threshold:0.7}") private val acquisitionThreshold: Double,
    @Value("\${trueticket.and-engine.habitual-threshold:0.7}") private val habitualThreshold: Double,
) {

    @Transactional
    fun applyAcquisitionScore(event: AcquisitionScoreEvent) {
        val pending = pendingScoreJoinRepository.findById(event.reservationSessionId)
            .orElse(PendingScoreJoin(reservationSessionId = event.reservationSessionId))

        pending.acquisitionScore = event.acquisitionFraudScore
        pending.updatedAt = Instant.now()
        evaluate(pendingScoreJoinRepository.save(pending))
    }

    @Transactional
    fun applyHabitualScore(event: HabitualScoreEvent) {
        val pending = pendingScoreJoinRepository.findById(event.reservationSessionId)
            .orElse(PendingScoreJoin(reservationSessionId = event.reservationSessionId))

        pending.habitualScore = event.habitualScore
        pending.listingId = event.listingId
        pending.updatedAt = Instant.now()
        evaluate(pendingScoreJoinRepository.save(pending))
    }

    private fun evaluate(pending: PendingScoreJoin) {
        if (!pending.isReadyToJudge()) return

        val acquisitionScore = requireNotNull(pending.acquisitionScore)
        val habitualScore = requireNotNull(pending.habitualScore)

        val verdict = if (acquisitionScore >= acquisitionThreshold && habitualScore >= habitualThreshold) {
            Verdict.SUSPECTED
        } else {
            Verdict.CLEAR
        }

        scamJudgmentRepository.insertIfAbsent(
            judgmentId = UUID.randomUUID(),
            reservationSessionId = pending.reservationSessionId,
            listingId = requireNotNull(pending.listingId),
            acquisitionScore = acquisitionScore,
            habitualScore = habitualScore,
            verdict = verdict.name,
            judgedAt = Instant.now(),
        )

        pendingScoreJoinRepository.delete(pending)
    }
}

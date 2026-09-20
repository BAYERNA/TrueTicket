package com.trueticket.notification.service

import com.trueticket.notification.repository.PendingScoreJoinRepository
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.scheduling.annotation.Scheduled
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.Instant
import java.time.temporal.ChronoUnit

/**
 * 두 Kafka 이벤트 중 하나가 영구적으로 유실되면 조인 버퍼가 완료되지 않는다. 일정 시간이
 * 지난 미완성 행을 정리해 pending_score_joins가 무제한 증가하지 않도록 한다.
 */
@Service
class PendingScoreCleanupService(
    private val pendingScoreJoinRepository: PendingScoreJoinRepository,
    @Value("\${trueticket.and-engine.pending-retention-hours:24}")
    private val retentionHours: Long,
) {
    private val log = LoggerFactory.getLogger(javaClass)

    @Scheduled(fixedDelayString = "\${trueticket.and-engine.cleanup-interval-ms:3600000}")
    @Transactional
    fun deleteExpiredPendingScores() {
        val cutoff = Instant.now().minus(retentionHours, ChronoUnit.HOURS)
        val deleted = pendingScoreJoinRepository.deleteByUpdatedAtBefore(cutoff)
        if (deleted > 0) {
            log.info("만료된 AND 엔진 조인 버퍼 {}건을 정리했습니다.", deleted)
        }
    }
}

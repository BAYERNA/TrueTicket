package com.trueticket.queue.service

import com.trueticket.queue.dto.QueueStatusResponse
import com.trueticket.queue.event.QueueChangedEvent
import org.springframework.context.ApplicationEventPublisher
import org.springframework.data.redis.core.StringRedisTemplate
import org.springframework.stereotype.Service
import java.time.Duration
import java.time.Instant

/**
 * FR-001: Redis Sorted Set 기반 가상대기열. score = 진입 시각(epoch millis)이므로
 * 먼저 들어온 세션일수록 낮은 score를 가져 자연스럽게 순번이 정렬된다.
 * 입장 허용(admit)은 대기열 앞쪽 N명을 꺼내 별도의 "admitted" Set으로 옮기고
 * TTL을 부여해, 입장 허용 후에도 좌석 선택을 하지 않고 방치하는 세션을 자동 만료시킨다.
 */
@Service
class VirtualQueueService(
    private val redisTemplate: StringRedisTemplate,
    private val eventPublisher: ApplicationEventPublisher,
) {

    companion object {
        private val ADMITTED_TTL: Duration = Duration.ofMinutes(5)
    }

    private fun waitingKey(eventId: String) = "queue:waiting:$eventId"
    private fun admittedKey(eventId: String, userId: String) = "queue:admitted:$eventId:$userId"

    fun join(eventId: String, userId: String): QueueStatusResponse {
        val zSetOps = redisTemplate.opsForZSet()
        zSetOps.addIfAbsent(waitingKey(eventId), userId, Instant.now().toEpochMilli().toDouble())
        eventPublisher.publishEvent(QueueChangedEvent(eventId))
        return status(eventId, userId)
    }

    fun status(eventId: String, userId: String): QueueStatusResponse {
        val zSetOps = redisTemplate.opsForZSet()
        val rank = zSetOps.rank(waitingKey(eventId), userId)
        val waitingCount = zSetOps.zCard(waitingKey(eventId)) ?: 0
        val admitted = redisTemplate.hasKey(admittedKey(eventId, userId))

        return QueueStatusResponse(
            eventId = eventId,
            userId = userId,
            rank = (rank ?: -1) + 1, // 0-based -> 1-based 순번
            waitingCount = waitingCount,
            admitted = admitted,
        )
    }

    /** 대기열 앞쪽 [count]명을 예매 화면으로 입장시킨다. 스케줄러나 운영자 트리거로 호출한다. */
    fun admitNext(eventId: String, count: Long): List<String> {
        val zSetOps = redisTemplate.opsForZSet()
        val candidates = zSetOps.range(waitingKey(eventId), 0, count - 1) ?: emptySet()

        candidates.forEach { userId ->
            zSetOps.remove(waitingKey(eventId), userId)
            redisTemplate.opsForValue().set(admittedKey(eventId, userId), "1", ADMITTED_TTL)
        }

        if (candidates.isNotEmpty()) {
            eventPublisher.publishEvent(QueueChangedEvent(eventId))
        }

        return candidates.toList()
    }
}

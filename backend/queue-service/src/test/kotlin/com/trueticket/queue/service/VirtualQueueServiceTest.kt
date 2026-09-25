package com.trueticket.queue.service

import com.trueticket.queue.event.QueueChangedEvent
import io.mockk.every
import io.mockk.mockk
import io.mockk.slot
import io.mockk.verify
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.springframework.context.ApplicationEventPublisher
import org.springframework.data.redis.core.StringRedisTemplate
import org.springframework.data.redis.core.ValueOperations
import org.springframework.data.redis.core.ZSetOperations
import java.time.Duration

class VirtualQueueServiceTest {
    private val redisTemplate = mockk<StringRedisTemplate>()
    private val zSetOps = mockk<ZSetOperations<String, String>>()
    private val valueOps = mockk<ValueOperations<String, String>>()
    private val eventPublisher = mockk<ApplicationEventPublisher>(relaxed = true)
    private val service = VirtualQueueService(redisTemplate, eventPublisher)

    @Test
    fun `join adds to the waiting set and publishes a QueueChangedEvent`() {
        every { redisTemplate.opsForZSet() } returns zSetOps
        every { zSetOps.addIfAbsent(any(), any(), any()) } returns true
        every { zSetOps.rank("queue:waiting:evt1", "user1") } returns 0L
        every { zSetOps.zCard("queue:waiting:evt1") } returns 1L
        every { redisTemplate.hasKey("queue:admitted:evt1:user1") } returns false

        val result = service.join("evt1", "user1")

        assertThat(result.rank).isEqualTo(1L)
        assertThat(result.waitingCount).isEqualTo(1L)
        assertThat(result.admitted).isFalse()

        val captured = slot<QueueChangedEvent>()
        verify { eventPublisher.publishEvent(capture(captured)) }
        assertThat(captured.captured.eventId).isEqualTo("evt1")
    }

    @Test
    fun `admitNext publishes a QueueChangedEvent only when someone was actually admitted`() {
        every { redisTemplate.opsForZSet() } returns zSetOps
        every { zSetOps.range("queue:waiting:evt1", 0, 9) } returns emptySet()

        service.admitNext("evt1", 10)

        verify(exactly = 0) { eventPublisher.publishEvent(any<QueueChangedEvent>()) }
    }

    @Test
    fun `admitNext moves candidates to admitted and publishes a QueueChangedEvent`() {
        every { redisTemplate.opsForZSet() } returns zSetOps
        every { zSetOps.range("queue:waiting:evt1", 0, 9) } returns linkedSetOf("user1", "user2")
        every { zSetOps.remove("queue:waiting:evt1", any()) } returns 1L
        every { redisTemplate.opsForValue() } returns valueOps
        every { valueOps.set(any(), any(), any<Duration>()) } returns Unit

        val admitted = service.admitNext("evt1", 10)

        assertThat(admitted).containsExactly("user1", "user2")
        verify { eventPublisher.publishEvent(match<QueueChangedEvent> { it.eventId == "evt1" }) }
    }
}

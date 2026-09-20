package com.trueticket.notification.service

import com.trueticket.notification.domain.PendingScoreJoin
import com.trueticket.notification.kafka.AcquisitionScoreEvent
import com.trueticket.notification.kafka.HabitualScoreEvent
import com.trueticket.notification.repository.PendingScoreJoinRepository
import com.trueticket.notification.repository.ScamJudgmentRepository
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.Optional
import java.util.UUID

class AndEngineServiceTest {
    private val pendingRepository = mockk<PendingScoreJoinRepository>()
    private val judgmentRepository = mockk<ScamJudgmentRepository>()
    private lateinit var service: AndEngineService
    private var storedPending: PendingScoreJoin? = null

    @BeforeEach
    fun setUp() {
        storedPending = null
        every { pendingRepository.findById(any()) } answers {
            Optional.ofNullable(storedPending)
        }
        every { pendingRepository.save(any()) } answers {
            firstArg<PendingScoreJoin>().also { storedPending = it }
        }
        every { pendingRepository.delete(any()) } answers {
            storedPending = null
            Unit
        }
        every {
            judgmentRepository.insertIfAbsent(any(), any(), any(), any(), any(), any(), any())
        } returns 1

        service = AndEngineService(
            pendingScoreJoinRepository = pendingRepository,
            scamJudgmentRepository = judgmentRepository,
            acquisitionThreshold = 0.7,
            habitualThreshold = 0.7,
        )
    }

    @Test
    fun `events arriving out of order are joined and judged once`() {
        val sessionId = UUID.randomUUID()
        val listingId = UUID.randomUUID()
        val verdicts = mutableListOf<String>()
        every {
            judgmentRepository.insertIfAbsent(any(), sessionId, listingId, 0.91, 0.82, any(), any())
        } answers {
            verdicts += arg<String>(5)
            1
        }

        service.applyHabitualScore(
            HabitualScoreEvent(sessionId, listingId, 0.82, true, Instant.now())
        )
        service.applyAcquisitionScore(
            AcquisitionScoreEvent(sessionId, 0.91, true, Instant.now())
        )

        assertEquals(listOf("SUSPECTED"), verdicts)
        verify(exactly = 1) {
            judgmentRepository.insertIfAbsent(any(), sessionId, listingId, 0.91, 0.82, "SUSPECTED", any())
        }
        verify(exactly = 1) { pendingRepository.delete(any()) }
    }

    @Test
    fun `one score below threshold produces clear verdict`() {
        val sessionId = UUID.randomUUID()
        val listingId = UUID.randomUUID()

        service.applyAcquisitionScore(
            AcquisitionScoreEvent(sessionId, 0.95, true, Instant.now())
        )
        service.applyHabitualScore(
            HabitualScoreEvent(sessionId, listingId, 0.4, false, Instant.now())
        )

        verify(exactly = 1) {
            judgmentRepository.insertIfAbsent(any(), sessionId, listingId, 0.95, 0.4, "CLEAR", any())
        }
    }
}

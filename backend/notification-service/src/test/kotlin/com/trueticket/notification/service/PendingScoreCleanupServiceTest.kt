package com.trueticket.notification.service

import com.trueticket.notification.repository.PendingScoreJoinRepository
import io.mockk.every
import io.mockk.mockk
import io.mockk.slot
import io.mockk.verify
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.time.Instant

class PendingScoreCleanupServiceTest {
    private val pendingRepository = mockk<PendingScoreJoinRepository>()

    @Test
    fun `pending joins older than retention window are deleted`() {
        val cutoff = slot<Instant>()
        every { pendingRepository.deleteByUpdatedAtBefore(capture(cutoff)) } returns 3
        val before = Instant.now().minusSeconds(24 * 60 * 60L + 2)

        PendingScoreCleanupService(pendingRepository, retentionHours = 24)
            .deleteExpiredPendingScores()

        val after = Instant.now().minusSeconds(24 * 60 * 60L - 2)
        assertTrue(cutoff.captured.isAfter(before))
        assertTrue(cutoff.captured.isBefore(after))
        verify(exactly = 1) { pendingRepository.deleteByUpdatedAtBefore(any()) }
    }
}

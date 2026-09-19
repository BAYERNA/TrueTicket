package com.trueticket.queue.dto

import jakarta.validation.constraints.NotBlank

data class JoinQueueRequest(
    @field:NotBlank val userId: String,
)

data class QueueStatusResponse(
    val eventId: String,
    val userId: String,
    val rank: Long,
    val waitingCount: Long,
    val admitted: Boolean,
)

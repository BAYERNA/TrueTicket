package com.trueticket.queue.dto

data class QueueStatusResponse(
    val eventId: String,
    val userId: String,
    val rank: Long,
    val waitingCount: Long,
    val admitted: Boolean,
)

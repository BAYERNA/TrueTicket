package com.trueticket.queue.controller

import com.trueticket.queue.dto.JoinQueueRequest
import com.trueticket.queue.dto.QueueStatusResponse
import com.trueticket.queue.service.VirtualQueueService
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/queue/{eventId}")
class QueueController(
    private val virtualQueueService: VirtualQueueService,
) {

    @PostMapping("/join")
    fun join(@PathVariable eventId: String, @RequestBody request: JoinQueueRequest): QueueStatusResponse =
        virtualQueueService.join(eventId, request.userId)

    @GetMapping("/status/{userId}")
    fun status(@PathVariable eventId: String, @PathVariable userId: String): QueueStatusResponse =
        virtualQueueService.status(eventId, userId)

    @PostMapping("/admit")
    fun admitNext(@PathVariable eventId: String, @RequestParam(defaultValue = "10") count: Long): List<String> =
        virtualQueueService.admitNext(eventId, count)
}

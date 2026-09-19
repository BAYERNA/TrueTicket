package com.trueticket.queue.controller

import com.trueticket.queue.dto.JoinQueueRequest
import com.trueticket.queue.dto.QueueStatusResponse
import com.trueticket.queue.exception.ForbiddenException
import com.trueticket.queue.service.VirtualQueueService
import jakarta.validation.Valid
import org.springframework.beans.factory.annotation.Value
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/queue/{eventId}")
class QueueController(
    private val virtualQueueService: VirtualQueueService,
    @Value("\${internal.admit-api-key}") private val admitApiKey: String,
) {

    @PostMapping("/join")
    fun join(@PathVariable eventId: String, @Valid @RequestBody request: JoinQueueRequest): QueueStatusResponse =
        virtualQueueService.join(eventId, request.userId)

    @GetMapping("/status/{userId}")
    fun status(@PathVariable eventId: String, @PathVariable userId: String): QueueStatusResponse =
        virtualQueueService.status(eventId, userId)

    /**
     * FR-001: 대기열 앞쪽 N명을 입장시키는 관리자/스케줄러 전용 액션. 게이트웨이에서는
     * 이 경로를 공개 라우팅하지 않지만, queue-service가 사설망 안에서라도 직접 호출될
     * 가능성에 대비해 내부 API 키를 한 번 더 검사한다 — 그렇지 않으면 누구나 이 엔드포인트를
     * 반복 호출해 가상대기열 자체를 무력화할 수 있다.
     */
    @PostMapping("/admit")
    fun admitNext(
        @PathVariable eventId: String,
        @RequestParam(defaultValue = "10") count: Long,
        @RequestHeader("X-Internal-Api-Key", required = false) apiKey: String?,
    ): List<String> {
        if (apiKey != admitApiKey) {
            throw ForbiddenException("관리자/스케줄러 전용 엔드포인트입니다.")
        }
        return virtualQueueService.admitNext(eventId, count)
    }
}

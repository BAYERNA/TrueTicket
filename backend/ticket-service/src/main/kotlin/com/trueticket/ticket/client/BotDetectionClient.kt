package com.trueticket.ticket.client

import org.springframework.cloud.openfeign.FeignClient
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import java.util.UUID

data class BehaviorScoreRequest(
    val reservationSessionId: UUID,
    val eventType: String,
)

data class BehaviorScoreResponse(
    val acquisitionFraudScore: Double,
    val isFlagged: Boolean,
)

/**
 * ticket-service → bot-detection-service 즉시 호출(Orchestration). 좌석 선점 직전에
 * 행동 기반 이상탐지 스코어를 조회해 비정상 세션의 예매 자체를 막는 용도로 사용한다.
 * 장애 전파 차단은 Resilience4j Circuit Breaker(ReservationService에서 CircuitBreakerFactory로 적용)로 처리한다.
 *
 * bot-detection-service는 FastAPI(Python)라 Eureka에 등록되지 않으므로, gateway-service의
 * AI Domain 라우팅과 동일하게 이름 기반 로드밸런싱 대신 고정 URL로 호출한다.
 */
@FeignClient(
    name = "bot-detection-service",
    url = "\${bot-detection-service.url:http://localhost:8081}",
    path = "/api/bot-detection",
)
interface BotDetectionClient {

    @PostMapping("/score")
    fun getScore(@RequestBody request: BehaviorScoreRequest): BehaviorScoreResponse
}

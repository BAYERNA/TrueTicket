package com.trueticket.notification.kafka

import com.fasterxml.jackson.databind.ObjectMapper
import com.trueticket.notification.service.AndEngineService
import org.springframework.kafka.annotation.KafkaListener
import org.springframework.stereotype.Component

/**
 * bot-detection-service·resale-monitor-service는 FastAPI(Python) 기반이라 Spring의
 * JsonSerializer 타입 헤더(__TypeId__)를 붙이지 않는다. 원시 JSON 문자열로 받아
 * Jackson으로 직접 역직렬화해 폴리글랏 프로듀서와의 결합을 느슨하게 유지한다.
 */
@Component
class AndEngineConsumer(
    private val andEngineService: AndEngineService,
    private val objectMapper: ObjectMapper,
) {

    @KafkaListener(topics = ["acquisition-fraud-scores"], groupId = "notification-service")
    fun onAcquisitionScore(payload: String) {
        val event = objectMapper.readValue(payload, AcquisitionScoreEvent::class.java)
        andEngineService.applyAcquisitionScore(event)
    }

    @KafkaListener(topics = ["habitual-resale-scores"], groupId = "notification-service")
    fun onHabitualScore(payload: String) {
        val event = objectMapper.readValue(payload, HabitualScoreEvent::class.java)
        andEngineService.applyHabitualScore(event)
    }
}

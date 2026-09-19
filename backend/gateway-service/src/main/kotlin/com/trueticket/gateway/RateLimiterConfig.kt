package com.trueticket.gateway

import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import reactor.core.publisher.Mono

/**
 * FR-015: 오픈런 트래픽에 대한 1차 방어(대기열 진입 전). 클라이언트 IP 기준으로
 * 요청 속도를 제한한다. 인증된 사용자 기준으로 세분화하려면 principal 기반으로 교체한다.
 */
@Configuration
class RateLimiterConfig {

    @Bean
    fun ipKeyResolver(): KeyResolver = KeyResolver { exchange ->
        val remoteAddress = exchange.request.remoteAddress?.address?.hostAddress ?: "unknown"
        Mono.just(remoteAddress)
    }
}

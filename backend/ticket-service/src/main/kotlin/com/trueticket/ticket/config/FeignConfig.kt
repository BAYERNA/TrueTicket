package com.trueticket.ticket.config

import org.springframework.cloud.openfeign.EnableFeignClients
import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import feign.RequestInterceptor

@Configuration
@EnableFeignClients(basePackages = ["com.trueticket.ticket.client"])
class FeignConfig {
    @Bean
    fun internalApiKeyInterceptor(
        @Value("\${security.internal-api-key}") internalApiKey: String,
    ): RequestInterceptor = RequestInterceptor { template ->
        template.header("X-Internal-Api-Key", internalApiKey)
    }
}

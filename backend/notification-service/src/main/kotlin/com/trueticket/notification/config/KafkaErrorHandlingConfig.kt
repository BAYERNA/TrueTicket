package com.trueticket.notification.config

import org.apache.kafka.common.TopicPartition
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.kafka.core.KafkaTemplate
import org.springframework.kafka.listener.DeadLetterPublishingRecoverer
import org.springframework.kafka.listener.DefaultErrorHandler
import org.springframework.util.backoff.ExponentialBackOff

@Configuration
class KafkaErrorHandlingConfig {
    @Bean
    fun kafkaErrorHandler(kafkaTemplate: KafkaTemplate<String, String>): DefaultErrorHandler {
        val recoverer = DeadLetterPublishingRecoverer(kafkaTemplate) { record, _ ->
            TopicPartition("${record.topic()}.DLT", record.partition())
        }
        val backOff = ExponentialBackOff(1_000L, 2.0).apply {
            maxInterval = 10_000L
            maxElapsedTime = 30_000L
        }
        return DefaultErrorHandler(recoverer, backOff).apply { setCommitRecovered(true) }
    }
}

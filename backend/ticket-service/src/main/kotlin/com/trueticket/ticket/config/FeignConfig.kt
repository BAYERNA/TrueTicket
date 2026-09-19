package com.trueticket.ticket.config

import org.springframework.cloud.openfeign.EnableFeignClients
import org.springframework.context.annotation.Configuration

@Configuration
@EnableFeignClients(basePackages = ["com.trueticket.ticket.client"])
class FeignConfig

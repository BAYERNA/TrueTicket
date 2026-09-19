package com.trueticket.ticket

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication
import org.springframework.cloud.client.discovery.EnableDiscoveryClient

@EnableDiscoveryClient
@SpringBootApplication
class TicketServiceApplication

fun main(args: Array<String>) {
    runApplication<TicketServiceApplication>(*args)
}

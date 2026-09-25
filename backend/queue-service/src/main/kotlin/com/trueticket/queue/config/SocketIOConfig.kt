package com.trueticket.queue.config

import com.corundumstudio.socketio.AuthorizationListener
import com.corundumstudio.socketio.AuthorizationResult
import com.corundumstudio.socketio.SocketIOServer
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.security.oauth2.jwt.JwtDecoder
import org.springframework.security.oauth2.jwt.JwtException

/**
 * queue-service의 REST API(Servlet 컨테이너)와는 별개의 포트에서 뜨는 Netty 기반
 * Socket.IO 서버. 프론트엔드의 socket.io-client가 대기열 순번을 실시간으로 받기
 * 위해 연결하는 대상이다.
 *
 * 핸드셰이크는 쿼리 파라미터로 전달된 JWT를 기존 REST API와 동일한 JwtDecoder로
 * 검증한다 — 별도의 인증 로직을 새로 만들지 않는다.
 */
@Configuration
class SocketIOConfig(
    @Value("\${socketio.port:9092}") private val socketIoPort: Int,
    private val jwtDecoder: JwtDecoder,
) {
    private val log = LoggerFactory.getLogger(SocketIOConfig::class.java)

    @Bean(destroyMethod = "stop")
    fun socketIOServer(): SocketIOServer {
        val configuration = com.corundumstudio.socketio.Configuration()
        configuration.hostname = "0.0.0.0"
        configuration.port = socketIoPort
        configuration.authorizationListener = AuthorizationListener { handshakeData ->
            val token = handshakeData.getSingleUrlParam("token")
            val eventId = handshakeData.getSingleUrlParam("eventId")
            if (token.isNullOrBlank() || eventId.isNullOrBlank()) {
                AuthorizationResult.FAILED_AUTHORIZATION
            } else {
                try {
                    val jwt = jwtDecoder.decode(token)
                    AuthorizationResult(true, mapOf("userId" to jwt.subject, "eventId" to eventId))
                } catch (e: JwtException) {
                    log.debug("Socket.IO 핸드셰이크 인증 실패", e)
                    AuthorizationResult.FAILED_AUTHORIZATION
                }
            }
        }

        val server = SocketIOServer(configuration)
        server.start()
        log.info("Socket.IO server started on port {}", socketIoPort)
        return server
    }
}

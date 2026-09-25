package com.trueticket.queue.socket

import com.corundumstudio.socketio.SocketIOClient
import com.corundumstudio.socketio.SocketIOServer
import com.trueticket.queue.event.QueueChangedEvent
import com.trueticket.queue.service.VirtualQueueService
import jakarta.annotation.PostConstruct
import org.slf4j.LoggerFactory
import org.springframework.context.event.EventListener
import org.springframework.stereotype.Component
import java.util.concurrent.ConcurrentHashMap

/**
 * 연결된 클라이언트를 이벤트별로 추적하고, 대기열 상태가 바뀔 때마다(QueueChangedEvent)
 * 접속 중인 사용자 각자에게 자신의 최신 순번을 계산해 푸시한다. 클라이언트마다 rank가
 * 다르므로 같은 payload를 방송하는 대신 사용자별로 개별 emit한다.
 */
@Component
class QueueSocketHandler(
    private val socketIOServer: SocketIOServer,
    private val virtualQueueService: VirtualQueueService,
) {
    private val log = LoggerFactory.getLogger(QueueSocketHandler::class.java)
    private val clientsByEvent = ConcurrentHashMap<String, MutableSet<SocketIOClient>>()

    @PostConstruct
    fun registerListeners() {
        socketIOServer.addConnectListener { client ->
            val eventId = client.get<String>("eventId")
            val userId = client.get<String>("userId")
            if (eventId == null || userId == null) {
                client.disconnect()
                return@addConnectListener
            }
            clientsByEvent.computeIfAbsent(eventId) { ConcurrentHashMap.newKeySet() }.add(client)
            log.debug("Socket.IO client connected: event={} user={}", eventId, userId)
            pushStatus(client, eventId, userId)
        }

        socketIOServer.addDisconnectListener { client ->
            val eventId = client.get<String>("eventId") ?: return@addDisconnectListener
            clientsByEvent[eventId]?.remove(client)
        }
    }

    @EventListener
    fun onQueueChanged(event: QueueChangedEvent) {
        val clients = clientsByEvent[event.eventId] ?: return
        clients.forEach { client ->
            val userId = client.get<String>("userId") ?: return@forEach
            pushStatus(client, event.eventId, userId)
        }
    }

    private fun pushStatus(client: SocketIOClient, eventId: String, userId: String) {
        val status = virtualQueueService.status(eventId, userId)
        client.sendEvent("queue:$eventId", status)
    }
}

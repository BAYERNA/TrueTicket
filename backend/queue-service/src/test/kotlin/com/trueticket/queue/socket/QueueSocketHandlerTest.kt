package com.trueticket.queue.socket

import com.corundumstudio.socketio.SocketIOClient
import com.corundumstudio.socketio.SocketIOServer
import com.corundumstudio.socketio.listener.ConnectListener
import com.corundumstudio.socketio.listener.DisconnectListener
import com.trueticket.queue.dto.QueueStatusResponse
import com.trueticket.queue.event.QueueChangedEvent
import com.trueticket.queue.service.VirtualQueueService
import io.mockk.every
import io.mockk.mockk
import io.mockk.slot
import io.mockk.verify
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test

class QueueSocketHandlerTest {
    private val socketIOServer = mockk<SocketIOServer>(relaxed = true)
    private val virtualQueueService = mockk<VirtualQueueService>()
    private val handler = QueueSocketHandler(socketIOServer, virtualQueueService)

    private lateinit var connectListener: ConnectListener
    private lateinit var disconnectListener: DisconnectListener

    @BeforeEach
    fun setUp() {
        val connectSlot = slot<ConnectListener>()
        val disconnectSlot = slot<DisconnectListener>()
        every { socketIOServer.addConnectListener(capture(connectSlot)) } returns Unit
        every { socketIOServer.addDisconnectListener(capture(disconnectSlot)) } returns Unit

        handler.registerListeners()

        connectListener = connectSlot.captured
        disconnectListener = disconnectSlot.captured
    }

    private fun client(eventId: String?, userId: String?): SocketIOClient {
        val client = mockk<SocketIOClient>(relaxed = true)
        every { client.get<String>("eventId") } returns eventId
        every { client.get<String>("userId") } returns userId
        return client
    }

    @Test
    fun `pushes the connecting user's own status right after connecting`() {
        val client = client("evt1", "user1")
        val status = QueueStatusResponse("evt1", "user1", 1, 1, false)
        every { virtualQueueService.status("evt1", "user1") } returns status

        connectListener.onConnect(client)

        verify { client.sendEvent("queue:evt1", status) }
    }

    @Test
    fun `disconnects a client whose handshake didn't resolve eventId or userId`() {
        val client = client(eventId = null, userId = "user1")

        connectListener.onConnect(client)

        verify { client.disconnect() }
        verify(exactly = 0) { client.sendEvent(any(), *anyVararg()) }
    }

    @Test
    fun `onQueueChanged pushes each connected client's own status, not a shared broadcast`() {
        val clientA = client("evt1", "userA")
        val clientB = client("evt1", "userB")
        val otherEventClient = client("evt2", "userC")
        val statusA = QueueStatusResponse("evt1", "userA", 1, 2, false)
        val statusB = QueueStatusResponse("evt1", "userB", 2, 2, false)
        every { virtualQueueService.status("evt1", "userA") } returns statusA
        every { virtualQueueService.status("evt1", "userB") } returns statusB
        every { virtualQueueService.status("evt2", "userC") } returns QueueStatusResponse("evt2", "userC", 1, 1, false)

        connectListener.onConnect(clientA)
        connectListener.onConnect(clientB)
        connectListener.onConnect(otherEventClient)

        handler.onQueueChanged(QueueChangedEvent("evt1"))

        verify(exactly = 2) { clientA.sendEvent("queue:evt1", statusA) }
        verify(exactly = 2) { clientB.sendEvent("queue:evt1", statusB) }
        verify(exactly = 0) { otherEventClient.sendEvent("queue:evt1", any()) }
    }

    @Test
    fun `stops pushing to a client after it disconnects`() {
        val client = client("evt1", "user1")
        val status = QueueStatusResponse("evt1", "user1", 1, 1, false)
        every { virtualQueueService.status("evt1", "user1") } returns status

        connectListener.onConnect(client)
        disconnectListener.onDisconnect(client)
        handler.onQueueChanged(QueueChangedEvent("evt1"))

        // 연결 시점의 1회 push만 있어야 하고, disconnect 이후의 QueueChangedEvent로는 더 이상 push되지 않아야 한다.
        verify(exactly = 1) { client.sendEvent("queue:evt1", status) }
    }
}

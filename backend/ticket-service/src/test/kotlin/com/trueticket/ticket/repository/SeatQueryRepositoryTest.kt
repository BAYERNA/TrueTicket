package com.trueticket.ticket.repository

import com.trueticket.ticket.KPostgreSQLContainer
import com.trueticket.ticket.config.QuerydslConfig
import com.trueticket.ticket.domain.Event
import com.trueticket.ticket.domain.EventCategory
import com.trueticket.ticket.domain.Seat
import com.trueticket.ticket.domain.SeatStatus
import jakarta.persistence.EntityManager
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase.Replace
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest
import org.springframework.context.annotation.Import
import org.springframework.test.context.DynamicPropertyRegistry
import org.springframework.test.context.DynamicPropertySource
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import java.math.BigDecimal
import java.time.Instant

@DataJpaTest
@AutoConfigureTestDatabase(replace = Replace.NONE)
@Import(QuerydslConfig::class, SeatQueryRepository::class)
@Testcontainers(disabledWithoutDocker = true)
class SeatQueryRepositoryTest {

    companion object {
        @Container
        @JvmStatic
        val postgres = KPostgreSQLContainer("postgres:16-alpine")
            .withDatabaseName("ticket_service")
            .withUsername("ticket")
            .withPassword("ticket")

        @DynamicPropertySource
        @JvmStatic
        fun registerProperties(registry: DynamicPropertyRegistry) {
            registry.add("spring.datasource.url", postgres::getJdbcUrl)
            registry.add("spring.datasource.username", postgres::getUsername)
            registry.add("spring.datasource.password", postgres::getPassword)
        }
    }

    @Autowired
    lateinit var entityManager: EntityManager

    @Autowired
    lateinit var seatQueryRepository: SeatQueryRepository

    private fun persistEvent(): Event {
        val event = Event(
            title = "테스트 콘서트",
            category = EventCategory.CONCERT,
            venue = "테스트 아레나",
            eventDatetime = Instant.now(),
            basePrice = BigDecimal("50000"),
        )
        entityManager.persist(event)
        return event
    }

    private fun persistSeat(event: Event, section: String, price: BigDecimal, status: SeatStatus) {
        entityManager.persist(
            Seat(
                eventId = event.id!!,
                seatSection = section,
                seatRow = "1",
                seatNumber = 1,
                price = price,
                status = status,
            ),
        )
    }

    @Test
    fun `filters by section, status, and price range only when each is provided`() {
        val event = persistEvent()
        persistSeat(event, section = "A", price = BigDecimal("50000"), status = SeatStatus.AVAILABLE)
        persistSeat(event, section = "A", price = BigDecimal("120000"), status = SeatStatus.AVAILABLE)
        persistSeat(event, section = "B", price = BigDecimal("50000"), status = SeatStatus.AVAILABLE)
        persistSeat(event, section = "A", price = BigDecimal("50000"), status = SeatStatus.SOLD)
        entityManager.flush()

        val noFilters = seatQueryRepository.search(event.id!!, null, null, null, null)
        assertThat(noFilters).hasSize(4)

        val sectionOnly = seatQueryRepository.search(event.id!!, "A", null, null, null)
        assertThat(sectionOnly).hasSize(3)

        val sectionAndStatus = seatQueryRepository.search(event.id!!, "A", SeatStatus.AVAILABLE, null, null)
        assertThat(sectionAndStatus).hasSize(2)

        val priceCapped = seatQueryRepository.search(
            event.id!!,
            "A",
            SeatStatus.AVAILABLE,
            null,
            BigDecimal("100000"),
        )
        assertThat(priceCapped).hasSize(1)
        assertThat(priceCapped.single().price).isEqualByComparingTo("50000")
    }
}

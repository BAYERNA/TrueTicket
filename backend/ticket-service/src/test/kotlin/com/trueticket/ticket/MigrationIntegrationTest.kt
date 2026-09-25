package com.trueticket.ticket

import org.assertj.core.api.Assertions.assertThat
import org.flywaydb.core.Flyway
import org.junit.jupiter.api.Test
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import java.sql.DriverManager

// Kotlin can't resolve the chained withXxx(...) calls on PostgreSQLContainer<Nothing> —
// Nothing can't stand in for the library's self-referential SELF type parameter. The
// standard workaround is a concrete subclass that closes the generic over itself.
class KPostgreSQLContainer(image: String) : PostgreSQLContainer<KPostgreSQLContainer>(image)

@Testcontainers(disabledWithoutDocker = true)
class MigrationIntegrationTest {
    companion object {
        @Container
        @JvmStatic
        val postgres = KPostgreSQLContainer("postgres:16-alpine")
            .withDatabaseName("ticket_service")
            .withUsername("ticket")
            .withPassword("ticket")
    }

    @Test
    fun `all migrations apply and payment lifecycle constraints exist`() {
        val result = Flyway.configure()
            .dataSource(postgres.jdbcUrl, postgres.username, postgres.password)
            .locations("classpath:db/migration")
            .load()
            .migrate()
        assertThat(result.success).isTrue()

        DriverManager.getConnection(postgres.jdbcUrl, postgres.username, postgres.password).use { connection ->
            connection.prepareStatement(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'payments'"
            ).use { statement ->
                val columns = buildSet {
                    statement.executeQuery().use { rows -> while (rows.next()) add(rows.getString(1)) }
                }
                assertThat(columns).contains("idempotency_key", "provider_payment_id", "webhook_event_id")
            }
        }
    }
}

package com.trueticket.notification

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
            .withDatabaseName("notification_service")
            .withUsername("notification")
            .withPassword("notification")
    }

    @Test
    fun `migrations enforce one judgment per session and listing`() {
        Flyway.configure()
            .dataSource(postgres.jdbcUrl, postgres.username, postgres.password)
            .locations("classpath:db/migration")
            .load()
            .migrate()

        DriverManager.getConnection(postgres.jdbcUrl, postgres.username, postgres.password).use { connection ->
            connection.prepareStatement(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'scam_judgments'"
            ).use { statement ->
                val indexes = buildSet {
                    statement.executeQuery().use { rows -> while (rows.next()) add(rows.getString(1)) }
                }
                // V2__judgment_idempotency.sql drops and recreates this index under its
                // original V1 name (idx_..., not uq_...) — it's the same UNIQUE index,
                // just not renamed when it was promoted to a constraint.
                assertThat(indexes).contains("idx_scam_judgments_session_listing")
            }
        }
    }
}

package com.trueticket.notification

import org.assertj.core.api.Assertions.assertThat
import org.flywaydb.core.Flyway
import org.junit.jupiter.api.Test
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import java.sql.DriverManager

@Testcontainers(disabledWithoutDocker = true)
class MigrationIntegrationTest {
    companion object {
        @Container
        @JvmStatic
        val postgres = PostgreSQLContainer<Nothing>("postgres:16-alpine")
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
                assertThat(indexes).contains("uq_scam_judgments_session_listing")
            }
        }
    }
}

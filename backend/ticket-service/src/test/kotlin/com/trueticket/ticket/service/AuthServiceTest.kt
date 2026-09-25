package com.trueticket.ticket.service

import com.trueticket.ticket.domain.User
import io.mockk.every
import io.mockk.mockk
import io.mockk.slot
import io.mockk.verify
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.springframework.security.crypto.password.PasswordEncoder
import org.springframework.security.oauth2.jwt.Jwt
import org.springframework.security.oauth2.jwt.JwtEncoder
import java.time.Instant
import java.util.UUID

class AuthServiceTest {
    private val userRepository = mockk<com.trueticket.ticket.repository.UserRepository>()
    private val passwordEncoder = mockk<PasswordEncoder>()
    private val jwtEncoder = mockk<JwtEncoder>()
    private val service = AuthService(userRepository, passwordEncoder, jwtEncoder, "trueticket", 60)

    @Test
    fun `findOrCreateOAuth2User reuses an existing account with the same email`() {
        val existing = User(id = UUID.randomUUID(), email = "user@example.com", passwordHash = "x", name = "Existing")
        every { userRepository.findByEmail("user@example.com") } returns existing

        val result = service.findOrCreateOAuth2User("User@Example.com", "Google Name")

        assertThat(result).isSameAs(existing)
        verify(exactly = 0) { userRepository.save(any()) }
    }

    @Test
    fun `findOrCreateOAuth2User creates a new account with an unusable random password hash`() {
        every { userRepository.findByEmail("new@example.com") } returns null
        every { passwordEncoder.encode(any()) } returns "bcrypt-hash-of-random-uuid"
        val savedSlot = slot<User>()
        every { userRepository.save(capture(savedSlot)) } answers { savedSlot.captured }

        val result = service.findOrCreateOAuth2User("new@example.com", "New User")

        assertThat(result.email).isEqualTo("new@example.com")
        assertThat(result.name).isEqualTo("New User")
        assertThat(result.passwordHash).isEqualTo("bcrypt-hash-of-random-uuid")
        // 무작위 값을 인코딩했는지(고정 문자열이 아닌지) 확인한다.
        verify { passwordEncoder.encode(match { it.isNotBlank() }) }
    }

    @Test
    fun `issueToken embeds the user's id, email, and role as JWT claims`() {
        val user = User(
            id = UUID.randomUUID(),
            email = "user@example.com",
            passwordHash = "x",
            name = "User",
        )
        val fakeJwt = mockk<Jwt>()
        every { fakeJwt.tokenValue } returns "signed.jwt.token"
        every { jwtEncoder.encode(any()) } returns fakeJwt

        val response = service.issueToken(user)

        assertThat(response.accessToken).isEqualTo("signed.jwt.token")
        assertThat(response.userId).isEqualTo(user.id)
        assertThat(response.email).isEqualTo("user@example.com")
        assertThat(response.expiresAt).isAfter(Instant.now())
    }
}

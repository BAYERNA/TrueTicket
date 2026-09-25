package com.trueticket.ticket.config

import com.trueticket.ticket.domain.User
import com.trueticket.ticket.domain.UserRole
import com.trueticket.ticket.dto.AuthResponse
import com.trueticket.ticket.service.AuthService
import io.mockk.every
import io.mockk.mockk
import io.mockk.slot
import io.mockk.verify
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.springframework.security.core.Authentication
import org.springframework.security.core.GrantedAuthority
import org.springframework.security.oauth2.core.user.OAuth2User
import java.time.Instant
import java.util.UUID

/** 테스트 전용 최소 OAuth2User — getAttribute(...)는 getAttributes()에 위임하는 디폴트 메서드라
 * mockk로 어설프게 흉내 내는 대신 실제 인터페이스를 그대로 구현하는 편이 더 정직하다. */
private class FakeOAuth2User(private val attributes: Map<String, Any>) : OAuth2User {
    override fun getAttributes(): Map<String, Any> = attributes
    override fun getAuthorities(): Collection<GrantedAuthority> = emptyList()
    override fun getName(): String = attributes["email"] as String
}

class OAuth2LoginSuccessHandlerTest {
    private val authService = mockk<AuthService>()
    private val handler = OAuth2LoginSuccessHandler(authService, "http://localhost:3000")

    @Test
    fun `mints a token via AuthService and redirects to the frontend callback with it`() {
        val oauth2User = FakeOAuth2User(mapOf("email" to "google-user@example.com", "name" to "Google User"))
        val authentication = mockk<Authentication>()
        every { authentication.principal } returns oauth2User

        val user = User(id = UUID.randomUUID(), email = "google-user@example.com", passwordHash = "x", name = "Google User")
        every { authService.findOrCreateOAuth2User("google-user@example.com", "Google User") } returns user

        val tokenResponse = AuthResponse(
            accessToken = "minted.jwt.token",
            expiresAt = Instant.now(),
            userId = user.id!!,
            email = user.email,
            role = UserRole.USER,
        )
        every { authService.issueToken(user) } returns tokenResponse

        val request = mockk<HttpServletRequest>()
        val response = mockk<HttpServletResponse>(relaxed = true)
        val redirectSlot = slot<String>()
        every { response.sendRedirect(capture(redirectSlot)) } returns Unit

        handler.onAuthenticationSuccess(request, response, authentication)

        verify { response.sendRedirect(any()) }
        val redirectUrl = redirectSlot.captured
        assertThat(redirectUrl).startsWith("http://localhost:3000/oauth2/callback?")
        assertThat(redirectUrl).contains("accessToken=minted.jwt.token")
        assertThat(redirectUrl).contains("userId=${user.id}")
        // '@'는 RFC 3986 query 컴포넌트에서 허용되는 문자라 UriComponentsBuilder가 퍼센트
        // 인코딩하지 않는다 — 실제 표준 동작이며 버그가 아니다.
        assertThat(redirectUrl).contains("email=google-user@example.com")
        assertThat(redirectUrl).contains("role=USER")
    }
}

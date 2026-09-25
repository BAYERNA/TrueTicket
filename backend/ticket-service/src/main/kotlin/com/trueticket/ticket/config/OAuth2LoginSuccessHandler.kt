package com.trueticket.ticket.config

import com.trueticket.ticket.service.AuthService
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.springframework.beans.factory.annotation.Value
import org.springframework.security.core.Authentication
import org.springframework.security.oauth2.core.user.OAuth2User
import org.springframework.security.web.authentication.AuthenticationSuccessHandler
import org.springframework.stereotype.Component
import org.springframework.web.util.UriComponentsBuilder

/**
 * Google 로그인 성공 후 기존 자체 발급 JWT와 동일한 형식의 토큰을 만들어 프론트엔드로
 * 돌려보낸다 — 다운스트림 서비스(게이트웨이, 다른 도메인 서비스)는 로그인 수단이
 * 이메일/비밀번호인지 소셜 로그인인지 구분할 필요가 없다.
 */
@Component
class OAuth2LoginSuccessHandler(
    private val authService: AuthService,
    @Value("\${frontend.origin}") private val frontendOrigin: String,
) : AuthenticationSuccessHandler {

    override fun onAuthenticationSuccess(
        request: HttpServletRequest,
        response: HttpServletResponse,
        authentication: Authentication,
    ) {
        val oauth2User = authentication.principal as OAuth2User
        val email = requireNotNull(oauth2User.getAttribute<String>("email")) {
            "Google OAuth2 프로필에 이메일이 없습니다."
        }
        val name = oauth2User.getAttribute<String>("name") ?: email

        val user = authService.findOrCreateOAuth2User(email, name)
        val tokenResponse = authService.issueToken(user)

        val redirectUrl = UriComponentsBuilder.fromUriString("$frontendOrigin/oauth2/callback")
            .queryParam("accessToken", tokenResponse.accessToken)
            .queryParam("userId", tokenResponse.userId)
            .queryParam("email", tokenResponse.email)
            .queryParam("role", tokenResponse.role)
            .build()
            .toUriString()

        response.sendRedirect(redirectUrl)
    }
}

package com.trueticket.ticket.service

import com.trueticket.ticket.domain.User
import com.trueticket.ticket.dto.AuthResponse
import com.trueticket.ticket.dto.LoginRequest
import com.trueticket.ticket.dto.RegisterRequest
import com.trueticket.ticket.exception.EmailAlreadyExistsException
import com.trueticket.ticket.exception.InvalidCredentialsException
import com.trueticket.ticket.repository.UserRepository
import org.springframework.beans.factory.annotation.Value
import org.springframework.security.crypto.password.PasswordEncoder
import org.springframework.security.oauth2.jose.jws.MacAlgorithm
import org.springframework.security.oauth2.jwt.JwtClaimsSet
import org.springframework.security.oauth2.jwt.JwtEncoder
import org.springframework.security.oauth2.jwt.JwtEncoderParameters
import org.springframework.security.oauth2.jwt.JwsHeader
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.Instant
import java.time.temporal.ChronoUnit
import java.util.UUID

@Service
class AuthService(
    private val userRepository: UserRepository,
    private val passwordEncoder: PasswordEncoder,
    private val jwtEncoder: JwtEncoder,
    @Value("\${security.jwt.issuer}") private val issuer: String,
    @Value("\${security.jwt.access-token-minutes}") private val accessTokenMinutes: Long,
) {
    @Transactional
    fun register(request: RegisterRequest): AuthResponse {
        val email = request.email.trim().lowercase()
        if (userRepository.findByEmail(email) != null) {
            throw EmailAlreadyExistsException(email)
        }
        val user = userRepository.save(
            User(
                email = email,
                passwordHash = passwordEncoder.encode(request.password),
                name = request.name.trim(),
                phone = request.phone?.trim()?.takeIf { it.isNotEmpty() },
            )
        )
        return issueToken(user)
    }

    @Transactional(readOnly = true)
    fun login(request: LoginRequest): AuthResponse {
        val user = userRepository.findByEmail(request.email.trim().lowercase())
            ?: throw InvalidCredentialsException()
        if (!passwordEncoder.matches(request.password, user.passwordHash)) {
            throw InvalidCredentialsException()
        }
        return issueToken(user)
    }

    /** Google 소셜 로그인: 이미 있는 이메일이면 재사용하고, 없으면 새로 만든다.
     * 비밀번호가 없는 계정이므로 아무도 알 수 없는 무작위 값을 해시해 채워 넣는다 —
     * password_hash 컬럼이 NOT NULL이지만, 이 해시로는 통상적인 이메일/비밀번호
     * 로그인이 성공할 수 없다.
     */
    @Transactional
    fun findOrCreateOAuth2User(email: String, name: String): User {
        val normalizedEmail = email.trim().lowercase()
        return userRepository.findByEmail(normalizedEmail) ?: userRepository.save(
            User(
                email = normalizedEmail,
                passwordHash = passwordEncoder.encode(UUID.randomUUID().toString()),
                name = name.trim().ifBlank { normalizedEmail },
            )
        )
    }

    fun issueToken(user: User): AuthResponse {
        val now = Instant.now()
        val expiresAt = now.plus(accessTokenMinutes, ChronoUnit.MINUTES)
        val userId = requireNotNull(user.id)
        val claims = JwtClaimsSet.builder()
            .issuer(issuer)
            .issuedAt(now)
            .expiresAt(expiresAt)
            .subject(userId.toString())
            .claim("email", user.email)
            .claim("roles", listOf(user.role.name))
            .build()
        val header = JwsHeader.with(MacAlgorithm.HS256).type("JWT").build()
        val token = jwtEncoder.encode(JwtEncoderParameters.from(header, claims)).tokenValue
        return AuthResponse(
            accessToken = token,
            expiresAt = expiresAt,
            userId = userId,
            email = user.email,
            role = user.role,
        )
    }
}

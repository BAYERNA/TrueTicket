package com.trueticket.ticket.config

import com.nimbusds.jose.jwk.source.ImmutableSecret
import com.nimbusds.jose.proc.SecurityContext
import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder
import org.springframework.security.crypto.password.PasswordEncoder
import org.springframework.security.oauth2.jose.jws.MacAlgorithm
import org.springframework.security.oauth2.jwt.JwtDecoder
import org.springframework.security.oauth2.jwt.JwtEncoder
import org.springframework.security.oauth2.jwt.JwtValidators
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder
import java.nio.charset.StandardCharsets
import javax.crypto.SecretKey
import javax.crypto.spec.SecretKeySpec

/**
 * PasswordEncoder/JwtEncoder/JwtDecoder는 원래 SecurityConfig 안에 있었지만,
 * AuthService(→ OAuth2LoginSuccessHandler → SecurityConfig)로 이어지는 순환 참조를
 * 만들었다 — SecurityConfig가 로그인 성공 핸들러를 생성자 주입받는 순간, 그 핸들러가
 * 필요로 하는 AuthService가 다시 SecurityConfig의 빈들을 필요로 하는 사이클이 생긴다.
 * 이 빈들을 별도 설정 클래스로 분리해 사이클을 끊는다.
 */
@Configuration
class SecurityBeansConfig(
    @Value("\${security.jwt.secret}") private val jwtSecret: String,
    @Value("\${security.jwt.issuer}") private val issuer: String,
) {
    @Bean
    fun passwordEncoder(): PasswordEncoder = BCryptPasswordEncoder()

    @Bean
    fun jwtEncoder(): JwtEncoder = NimbusJwtEncoder(ImmutableSecret<SecurityContext>(secretKey()))

    @Bean
    fun jwtDecoder(): JwtDecoder {
        val decoder = NimbusJwtDecoder.withSecretKey(secretKey())
            .macAlgorithm(MacAlgorithm.HS256)
            .build()
        decoder.setJwtValidator(JwtValidators.createDefaultWithIssuer(issuer))
        return decoder
    }

    private fun secretKey(): SecretKey {
        require(jwtSecret.toByteArray(StandardCharsets.UTF_8).size >= 32) {
            "JWT_SECRET must contain at least 32 bytes"
        }
        return SecretKeySpec(jwtSecret.toByteArray(StandardCharsets.UTF_8), "HmacSHA256")
    }
}

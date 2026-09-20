package com.trueticket.gateway.config

import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.http.HttpMethod
import org.springframework.security.config.web.server.ServerHttpSecurity
import org.springframework.security.oauth2.jose.jws.MacAlgorithm
import org.springframework.security.oauth2.jwt.JwtValidators
import org.springframework.security.oauth2.jwt.NimbusReactiveJwtDecoder
import org.springframework.security.oauth2.jwt.ReactiveJwtDecoder
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter
import org.springframework.security.oauth2.server.resource.authentication.JwtGrantedAuthoritiesConverter
import org.springframework.security.oauth2.server.resource.authentication.ReactiveJwtAuthenticationConverterAdapter
import org.springframework.security.web.server.SecurityWebFilterChain
import java.nio.charset.StandardCharsets
import javax.crypto.SecretKey
import javax.crypto.spec.SecretKeySpec

@Configuration
class SecurityConfig(
    @Value("\${security.jwt.secret}") private val jwtSecret: String,
    @Value("\${security.jwt.issuer}") private val issuer: String,
) {
    @Bean
    fun securityWebFilterChain(http: ServerHttpSecurity): SecurityWebFilterChain {
        http
            .csrf { it.disable() }
            .authorizeExchange {
                it.pathMatchers("/api/auth/**", "/actuator/health", "/actuator/info").permitAll()
                it.pathMatchers(HttpMethod.GET, "/api/events", "/api/events/**").permitAll()
                it.pathMatchers("/api/resale-monitor/**", "/api/judgments/**").hasRole("ADMIN")
                it.pathMatchers("/api/verification/**").hasAnyRole("STAFF", "ADMIN")
                it.anyExchange().authenticated()
            }
            .oauth2ResourceServer { oauth2 ->
                oauth2.jwt { jwt ->
                    jwt.jwtAuthenticationConverter(
                        ReactiveJwtAuthenticationConverterAdapter(jwtAuthenticationConverter())
                    )
                }
            }
        return http.build()
    }

    @Bean
    fun jwtDecoder(): ReactiveJwtDecoder {
        val decoder = NimbusReactiveJwtDecoder.withSecretKey(secretKey())
            .macAlgorithm(MacAlgorithm.HS256)
            .build()
        decoder.setJwtValidator(JwtValidators.createDefaultWithIssuer(issuer))
        return decoder
    }

    private fun jwtAuthenticationConverter(): JwtAuthenticationConverter {
        val authorities = JwtGrantedAuthoritiesConverter().apply {
            setAuthoritiesClaimName("roles")
            setAuthorityPrefix("ROLE_")
        }
        return JwtAuthenticationConverter().apply {
            setJwtGrantedAuthoritiesConverter(authorities)
        }
    }

    private fun secretKey(): SecretKey {
        require(jwtSecret.toByteArray(StandardCharsets.UTF_8).size >= 32) {
            "JWT_SECRET must contain at least 32 bytes"
        }
        return SecretKeySpec(jwtSecret.toByteArray(StandardCharsets.UTF_8), "HmacSHA256")
    }
}

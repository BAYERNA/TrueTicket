package com.trueticket.ticket.config

import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.http.HttpMethod
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity
import org.springframework.security.config.annotation.web.builders.HttpSecurity
import org.springframework.security.config.http.SessionCreationPolicy
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter
import org.springframework.security.oauth2.server.resource.authentication.JwtGrantedAuthoritiesConverter
import org.springframework.security.web.SecurityFilterChain

@Configuration
@EnableMethodSecurity
class SecurityConfig(
    private val oAuth2LoginSuccessHandler: OAuth2LoginSuccessHandler,
) {
    @Bean
    fun securityFilterChain(http: HttpSecurity): SecurityFilterChain {
        http
            .csrf { it.disable() }
            // OAuth2 로그인은 리다이렉트 왕복 동안 state/PKCE를 세션에 저장해야 한다 —
            // 그래서 완전한 STATELESS 대신 IF_REQUIRED를 쓴다. API 요청 자체는 여전히
            // Bearer 토큰만으로 인증되므로 세션을 만들지 않는다.
            .sessionManagement { it.sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED) }
            .authorizeHttpRequests {
                it.requestMatchers("/api/auth/**", "/actuator/health", "/actuator/info").permitAll()
                it.requestMatchers("/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll()
                it.requestMatchers("/oauth2/**", "/login/oauth2/**").permitAll()
                it.requestMatchers(HttpMethod.GET, "/api/events", "/api/events/**").permitAll()
                it.requestMatchers(HttpMethod.GET, "/api/reservations/qr/**").permitAll()
                it.requestMatchers(HttpMethod.POST, "/api/payments/webhooks/mock").permitAll()
                it.anyRequest().authenticated()
            }
            .oauth2ResourceServer { oauth2 ->
                oauth2.jwt { jwt -> jwt.jwtAuthenticationConverter(jwtAuthenticationConverter()) }
            }
            .oauth2Login { oauth2 ->
                oauth2.successHandler(oAuth2LoginSuccessHandler)
            }
        return http.build()
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
}

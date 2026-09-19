package com.trueticket.ticket.domain

import jakarta.persistence.*
import java.time.Instant
import java.util.UUID

enum class UserRole { USER, ORGANIZER, ADMIN }

@Entity
@Table(name = "users")
class User(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "user_id")
    val id: UUID? = null,

    @Column(nullable = false, unique = true)
    var email: String,

    @Column(name = "password_hash", nullable = false)
    var passwordHash: String,

    var name: String,

    var phone: String? = null,

    @Enumerated(EnumType.STRING)
    var role: UserRole = UserRole.USER,

    @Column(name = "created_at", nullable = false, updatable = false)
    val createdAt: Instant = Instant.now(),
)

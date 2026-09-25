package com.trueticket.notification.domain

import jakarta.persistence.*
import java.time.Instant
import java.util.UUID

enum class Verdict { SUSPECTED, CLEAR }

/**
 * FR-009-1: AND 엔진(취득 부정성 스코어 × 상습 판매 스코어)의 최종 판정 결과를 영속화한다.
 * 두 스코어가 모두 임계치를 초과할 때만 SUSPECTED로 판정하며, 어느 한쪽만 초과하면
 * CLEAR로 기록해 오탐 이의제기 대응 근거로 최소 1년 보관한다(NFR-007).
 */
@Entity
@Table(name = "scam_judgments")
class ScamJudgment(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "judgment_id")
    val id: UUID? = null,

    @Column(name = "reservation_session_id", nullable = false)
    var reservationSessionId: UUID,

    @Column(name = "listing_id")
    var listingId: UUID? = null,

    @Column(name = "acquisition_score", nullable = false)
    var acquisitionScore: Double,

    @Column(name = "habitual_score", nullable = false)
    var habitualScore: Double,

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    var verdict: Verdict,

    @Column(name = "judged_at", nullable = false, updatable = false)
    val judgedAt: Instant = Instant.now(),

    @Column(name = "reviewed_by")
    var reviewedBy: String? = null,
)

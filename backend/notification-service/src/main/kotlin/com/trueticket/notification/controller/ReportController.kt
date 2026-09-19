package com.trueticket.notification.controller

import com.trueticket.notification.domain.Report
import com.trueticket.notification.repository.ReportRepository
import jakarta.validation.Valid
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.NotNull
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*
import java.util.UUID

data class CreateReportRequest(
    @field:NotNull val reporterUserId: UUID,
    val targetListingId: UUID?,
    @field:NotBlank val reportReason: String,
)

/** FR-013: 이상거래 신고 접수. */
@RestController
@RequestMapping("/api/reports")
class ReportController(
    private val reportRepository: ReportRepository,
) {

    @PostMapping
    fun submit(@Valid @RequestBody request: CreateReportRequest): ResponseEntity<Report> {
        val report = reportRepository.save(
            Report(
                reporterUserId = request.reporterUserId,
                targetListingId = request.targetListingId,
                reportReason = request.reportReason,
            )
        )
        return ResponseEntity.status(HttpStatus.CREATED).body(report)
    }
}

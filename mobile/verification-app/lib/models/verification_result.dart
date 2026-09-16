/// verification-service의 POST /api/verification/verify 응답 (FR-010/FR-011).
class VerificationResult {
  VerificationResult({
    required this.verificationId,
    required this.reservationId,
    required this.faceMatchResult,
    required this.faceMatchScore,
    required this.duplicateScanFlag,
    required this.snapshotUri,
  });

  factory VerificationResult.fromJson(Map<String, dynamic> json) {
    return VerificationResult(
      verificationId: json['verification_id'] as String,
      reservationId: json['reservation_id'] as String,
      faceMatchResult: json['face_match_result'] as bool,
      faceMatchScore: (json['face_match_score'] as num).toDouble(),
      duplicateScanFlag: json['duplicate_scan_flag'] as bool,
      snapshotUri: json['snapshot_uri'] as String,
    );
  }

  final String verificationId;
  final String reservationId;
  final bool faceMatchResult;
  final double faceMatchScore;
  final bool duplicateScanFlag;
  final String snapshotUri;
}

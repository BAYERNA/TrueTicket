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
      verificationId: json['verificationId'] as String,
      reservationId: json['reservationId'] as String,
      faceMatchResult: json['faceMatchResult'] as bool,
      faceMatchScore: (json['faceMatchScore'] as num).toDouble(),
      duplicateScanFlag: json['duplicateScanFlag'] as bool,
      snapshotUri: json['snapshotUri'] as String,
    );
  }

  final String verificationId;
  final String reservationId;
  final bool faceMatchResult;
  final double faceMatchScore;
  final bool duplicateScanFlag;
  final String snapshotUri;
}

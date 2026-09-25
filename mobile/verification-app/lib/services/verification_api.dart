import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../models/verification_result.dart';

class VerificationApiException implements Exception {
  VerificationApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// FR-010/FR-011: QR 코드와 두 장의 이미지(현장 캡처, 신분증)를 verification-service로 전송한다.
/// 개발 중에는 verification-service(8093)에 직접 붙고, 배포 시 Gateway 경유로 바꾸려면
/// baseUrl만 교체하면 된다.
class VerificationApi {
  VerificationApi({this.baseUrl = 'http://localhost:8080'});

  final String baseUrl;

  Future<VerificationResult> verify({
    required String qrCode,
    required String accessToken,
    required File liveImage,
    required File referenceImage,
  }) async {
    final uri = Uri.parse('$baseUrl/api/verification/verify');
    final request = http.MultipartRequest('POST', uri)
      ..fields['qr_code'] = qrCode
      ..headers['Authorization'] = 'Bearer $accessToken'
      ..files.add(await http.MultipartFile.fromPath('live_image', liveImage.path))
      ..files.add(await http.MultipartFile.fromPath('reference_image', referenceImage.path));

    final streamedResponse = await request.send().timeout(const Duration(seconds: 15));
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode != 200) {
      String detail = '검증에 실패했습니다 (HTTP ${response.statusCode})';
      try {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        detail = body['detail']?.toString() ?? detail;
      } catch (_) {
        // 응답이 JSON이 아닌 경우 기본 메시지를 사용한다.
      }
      throw VerificationApiException(detail);
    }

    return VerificationResult.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }
}

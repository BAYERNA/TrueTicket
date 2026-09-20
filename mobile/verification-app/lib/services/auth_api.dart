import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class StaffSession {
  const StaffSession({required this.accessToken, required this.email, required this.role});
  final String accessToken;
  final String email;
  final String role;
}

class AuthApi {
  AuthApi({this.baseUrl = 'http://localhost:8080'});
  final String baseUrl;
  static const _storage = FlutterSecureStorage();

  Future<StaffSession> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    ).timeout(const Duration(seconds: 10));
    if (response.statusCode != 200) throw Exception('로그인 정보를 확인해주세요.');
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final role = body['role'] as String;
    if (role != 'STAFF' && role != 'ADMIN') throw Exception('검표 권한이 없는 계정입니다.');
    final session = StaffSession(
      accessToken: body['accessToken'] as String,
      email: body['email'] as String,
      role: role,
    );
    await _storage.write(key: 'access_token', value: session.accessToken);
    return session;
  }

  Future<String?> savedToken() => _storage.read(key: 'access_token');
  Future<void> logout() => _storage.delete(key: 'access_token');
}

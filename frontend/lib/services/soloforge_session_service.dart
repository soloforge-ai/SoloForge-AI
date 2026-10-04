import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

import 'pollinations_session_service.dart';

class SoloForgeSessionException implements Exception {
  const SoloForgeSessionException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// Backend owner session obtained only from a persisted Supabase GitHub login.
/// Pollinations credentials are separate and never authorize private APIs.
class SoloForgeSessionService {
  SoloForgeSessionService({http.Client? client, FlutterSecureStorage? storage})
      : _client = client ?? http.Client(),
        _storage = storage ?? const FlutterSecureStorage();

  static const _sessionKey = 'soloforge_session_token';
  static const _expiresAtKey = 'soloforge_session_expires_at';
  static const _refreshWindowSeconds = 5 * 60;

  final http.Client _client;
  final FlutterSecureStorage _storage;

  String get _baseUrl => assetForgeApiUrl.trim().replaceFirst(RegExp(r'/$'), '');

  Future<String?> readSessionToken() => _storage.read(key: _sessionKey);

  Future<Map<String, String>> authorizationHeaders() async {
    final token = await _ensureSession();
    return {'Authorization': 'Bearer $token'};
  }

  Future<String> _ensureSession() async {
    // A stored app token alone must not unlock a signed-out device.
    if (Supabase.instance.client.auth.currentSession == null) {
      await _clearAppSession();
      throw const SoloForgeSessionException('Sign in with GitHub to continue.');
    }
    final current = await readSessionToken();
    if (current != null && current.isNotEmpty) {
      if (await _status(current)) {
        await _refreshIfNeeded();
        return (await readSessionToken()) ?? current;
      }
      await _clearAppSession();
    }
    return _bootstrapOwnerSession();
  }

  Future<bool> _status(String token) async {
    final response = await _client.get(
      Uri.parse('$_baseUrl/auth/soloforge/status'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode < 200 || response.statusCode >= 300) return false;
    final body = jsonDecode(response.body);
    return body is Map && body['authenticated'] == true;
  }

  Future<void> _refreshIfNeeded() async {
    final raw = await _storage.read(key: _expiresAtKey);
    final expiresAt = int.tryParse(raw ?? '');
    final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    if (expiresAt != null && expiresAt - now > _refreshWindowSeconds) return;
    final supabaseToken = Supabase.instance.client.auth.currentSession?.accessToken;
    if (supabaseToken == null) return;
    final response = await _client.post(
      Uri.parse('$_baseUrl/auth/soloforge/refresh'),
      headers: {'Authorization': 'Bearer $supabaseToken'},
    );
    if (response.statusCode >= 200 && response.statusCode < 300) {
      await _storeResponse(response);
    }
  }

  Future<String> _bootstrapOwnerSession() async {
    final accessToken = Supabase.instance.client.auth.currentSession?.accessToken;
    if (accessToken == null || accessToken.isEmpty) {
      throw const SoloForgeSessionException('Sign in with GitHub to continue.');
    }
    final response = await _client.post(
      Uri.parse('$_baseUrl/auth/soloforge/bootstrap'),
      headers: {'Authorization': 'Bearer $accessToken'},
    );
    if (response.statusCode != 200) {
      throw const SoloForgeSessionException(
        'This GitHub identity is not authorized as the SoloForge owner.',
      );
    }
    return _storeResponse(response);
  }

  Future<String> _storeResponse(http.Response response) async {
    final body = jsonDecode(response.body);
    if (body is! Map) {
      throw const SoloForgeSessionException('Invalid SoloForge session response.');
    }
    final token = body['session_token']?.toString();
    if (token == null || token.isEmpty) {
      throw const SoloForgeSessionException('SoloForge session token is missing.');
    }
    await _storage.write(key: _sessionKey, value: token);
    final expiresAt = body['expires_at']?.toString();
    if (expiresAt != null && expiresAt.isNotEmpty) {
      await _storage.write(key: _expiresAtKey, value: expiresAt);
    }
    return token;
  }

  Future<void> _clearAppSession() async {
    await _storage.delete(key: _sessionKey);
    await _storage.delete(key: _expiresAtKey);
  }

  Future<void> clear() => _clearAppSession();

  void dispose() {
    _client.close();
  }
}

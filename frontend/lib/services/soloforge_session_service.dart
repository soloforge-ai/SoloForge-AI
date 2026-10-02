import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'pollinations_session_service.dart';

class SoloForgeSessionException implements Exception {
  const SoloForgeSessionException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// First-party application session.
///
/// Pollinations is used only as a one-time migration proof when an existing
/// SoloForge app session is not present. Provider credentials remain stored
/// separately and are never returned as the application bearer token.
class SoloForgeSessionService {
  SoloForgeSessionService({
    http.Client? client,
    FlutterSecureStorage? storage,
    PollinationsSessionService? legacySessionService,
  })  : _client = client ?? http.Client(),
        _storage = storage ?? const FlutterSecureStorage(),
        _legacySessionService =
            legacySessionService ?? PollinationsSessionService();

  static const _sessionKey = 'soloforge_session_token';
  static const _expiresAtKey = 'soloforge_session_expires_at';
  static const _refreshWindowSeconds = 7 * 24 * 60 * 60;

  final http.Client _client;
  final FlutterSecureStorage _storage;
  final PollinationsSessionService _legacySessionService;

  String get _baseUrl =>
      assetForgeApiUrl.trim().replaceFirst(RegExp(r'/$'), '');

  Future<String?> readSessionToken() => _storage.read(key: _sessionKey);

  Future<Map<String, String>> authorizationHeaders() async {
    final token = await _ensureSession();
    return {'Authorization': 'Bearer $token'};
  }

  Future<String> _ensureSession() async {
    final current = await readSessionToken();
    if (current != null && current.isNotEmpty) {
      final valid = await _status(current);
      if (valid) {
        await _refreshIfNeeded(current);
        return (await readSessionToken()) ?? current;
      }
      await _clearAppSession();
    }

    return _migrateLegacySession();
  }

  Future<bool> _status(String token) async {
    final response = await _client.get(
      Uri.parse('$_baseUrl/auth/soloforge/status'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      return false;
    }
    final body = jsonDecode(response.body);
    return body is Map && body['authenticated'] == true;
  }

  Future<void> _refreshIfNeeded(String token) async {
    final raw = await _storage.read(key: _expiresAtKey);
    final expiresAt = int.tryParse(raw ?? '');
    final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    if (expiresAt != null && expiresAt - now > _refreshWindowSeconds) {
      return;
    }

    final response = await _client.post(
      Uri.parse('$_baseUrl/auth/soloforge/refresh'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode >= 200 && response.statusCode < 300) {
      await _storeResponse(response);
    }
  }

  Future<String> _migrateLegacySession() async {
    final legacyToken = await _legacySessionService.readSessionToken();
    if (legacyToken == null || legacyToken.isEmpty) {
      throw const SoloForgeSessionException(
        'SoloForge app session is not initialized on this device.',
      );
    }

    final response = await _client.post(
      Uri.parse('$_baseUrl/auth/soloforge/exchange'),
      headers: {'Authorization': 'Bearer $legacyToken'},
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw const SoloForgeSessionException(
        'Could not migrate the existing SoloForge session.',
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

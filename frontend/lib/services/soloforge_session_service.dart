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

typedef OwnerIdentity = ({String userId, String accessToken});

/// Requests a short-lived backend session for the current GitHub identity.
/// No app bearer is cached, so an account switch cannot reuse an owner's token.
class SoloForgeSessionService {
  SoloForgeSessionService({
    http.Client? client,
    FlutterSecureStorage? storage,
    OwnerIdentity? Function()? currentIdentity,
  })  : _client = client ?? http.Client(),
        _storage = storage ?? const FlutterSecureStorage(),
        _currentIdentity = currentIdentity ?? _supabaseIdentity;

  static const _legacySessionKey = 'soloforge_session_token';
  static const _legacyExpiresAtKey = 'soloforge_session_expires_at';
  static const _legacyOwnerKey = 'soloforge_session_owner_user_id';

  final http.Client _client;
  final FlutterSecureStorage _storage;
  final OwnerIdentity? Function() _currentIdentity;

  static OwnerIdentity? _supabaseIdentity() {
    final auth = Supabase.instance.client.auth;
    final session = auth.currentSession;
    final userId = auth.currentUser?.id;
    if (session == null || userId == null) return null;
    return (userId: userId, accessToken: session.accessToken);
  }

  String get _baseUrl => assetForgeApiUrl.trim().replaceFirst(RegExp(r'/$'), '');

  Future<Map<String, String>> authorizationHeaders() async {
    final identity = _currentIdentity();
    if (identity == null) {
      throw const SoloForgeSessionException('Sign in with GitHub to continue.');
    }
    final response = await _client.post(
      Uri.parse('$_baseUrl/auth/soloforge/bootstrap'),
      headers: {'Authorization': 'Bearer ${identity.accessToken}'},
    );
    // OAuth state can change while the request is in flight. Never return an
    // owner bearer to a different or signed-out account on the same device.
    if (_currentIdentity()?.userId != identity.userId) {
      throw const SoloForgeSessionException('GitHub account changed. Please retry.');
    }
    if (response.statusCode != 200) {
      throw const SoloForgeSessionException(
        'This GitHub identity is not authorized as the SoloForge owner.',
      );
    }
    final body = jsonDecode(response.body);
    if (body is! Map || body['session_token'] is! String ||
        (body['session_token'] as String).isEmpty) {
      throw const SoloForgeSessionException('Invalid SoloForge session response.');
    }
    return {'Authorization': 'Bearer ${body['session_token']}'};
  }

  /// Remove any v1/v2 tokens left by older APKs; no new app token is stored.
  Future<void> clear() async {
    await _storage.delete(key: _legacySessionKey);
    await _storage.delete(key: _legacyExpiresAtKey);
    await _storage.delete(key: _legacyOwnerKey);
  }

  void dispose() {
    _client.close();
  }
}

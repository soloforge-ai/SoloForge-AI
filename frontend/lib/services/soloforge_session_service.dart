import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

import 'pollinations_session_service.dart';
import 'owner_v2_session_service.dart';

class SoloForgeSessionException implements Exception {
  const SoloForgeSessionException(this.message);
  final String message;
  @override
  String toString() => message;
}

typedef OwnerIdentity = ({String userId, String accessToken});

/// Selects the opt-in V2 authority or the retained GitHub bootstrap.
/// A V2 failure never falls back to a legacy bearer.
class SoloForgeSessionService {
  SoloForgeSessionService({
    http.Client? client,
    FlutterSecureStorage? storage,
    OwnerIdentity? Function()? currentIdentity,
    OwnerV2SessionService? ownerV2Session,
    this.useOwnerV2 = ownerV2Enabled,
  }) : _ownerV2 = ownerV2Session ?? OwnerV2SessionService.shared,
       _client = client ?? http.Client(),
       _storage = storage ?? const FlutterSecureStorage(),
       _currentIdentity = currentIdentity ?? _supabaseIdentity;

  static const _legacySessionKey = 'soloforge_session_token';
  static const _legacyExpiresAtKey = 'soloforge_session_expires_at';
  static const _legacyOwnerKey = 'soloforge_session_owner_user_id';

  final OwnerV2SessionService _ownerV2;
  static String? _v2Token;
  static String? _v2UserId;
  final bool useOwnerV2;
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

  String get _baseUrl =>
      assetForgeApiUrl.trim().replaceFirst(RegExp(r'/$'), '');

  Future<Map<String, String>> authorizationHeaders() async {
    final identity = _currentIdentity();
    if (useOwnerV2 && _v2Token != null) {
      if (identity?.userId != _v2UserId) {
        _v2Token = null;
        _v2UserId = null;
      } else {
        final response = await _client.get(
          Uri.parse('$_baseUrl/auth/owner-v2/session'),
          headers: {'Authorization': 'Bearer $_v2Token'},
        );
        if (response.statusCode == 200) {
          final body = jsonDecode(response.body);
          if (body is Map && body['authenticated'] == true &&
              body['identity_version'] == 'owner_v2') {
            return {'Authorization': 'Bearer $_v2Token'};
          }
        }
        _v2Token = null;
        _v2UserId = null;
        throw const SoloForgeSessionException('Owner V2 session expired. Sign in again.');
      }
    }
    if (identity == null) {
      throw const SoloForgeSessionException('Sign in with GitHub to continue.');
    }
    final response = await _client.post(
      Uri.parse('$_baseUrl/auth/soloforge/${useOwnerV2 ? 'bootstrap-v2' : 'bootstrap'}'),
      headers: {'Authorization': 'Bearer ${identity.accessToken}'},
    );
    // OAuth state can change while the request is in flight. Never return an
    // owner bearer to a different or signed-out account on the same device.
    if (_currentIdentity()?.userId != identity.userId) {
      throw const SoloForgeSessionException(
        'GitHub account changed. Please retry.',
      );
    }
    if (response.statusCode != 200) {
      throw const SoloForgeSessionException(
        'This GitHub identity is not authorized as the SoloForge owner.',
      );
    }
    final body = jsonDecode(response.body);
    if (body is! Map ||
        body['session_token'] is! String ||
        (body['session_token'] as String).isEmpty) {
      throw const SoloForgeSessionException(
        'Invalid SoloForge session response.',
      );
    }
    if (useOwnerV2) {
      final token = body['session_token'] as String;
      if (!RegExp(r'^sf_owner_v2_[A-Za-z0-9_-]{43}
  }

  /// Revoke only the app's V2 bearer. GitHub OAuth remains connected.
  Future<void> logoutV2() async {
    final token = _v2Token;
    _v2Token = null;
    _v2UserId = null;
    if (token == null) return;
    final response = await _client.post(
      Uri.parse('$_baseUrl/auth/owner-v2/logout'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 204) {
      throw const SoloForgeSessionException('Server logout could not be confirmed.');
    }
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
).hasMatch(token) ||
          body['identity_version'] != 'owner_v2' ||
          body['authenticated'] != true) {
        throw const SoloForgeSessionException('Invalid Owner V2 identity response.');
      }
    }
    if (useOwnerV2) {
      _v2Token = body['session_token'] as String;
      _v2UserId = identity.userId;
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

import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'pollinations_session_service.dart';

const ownerV2Enabled = bool.fromEnvironment('SOLOFORGE_OWNER_V2');

/// Shared in-process identity. No codes, proofs or bearers enter disk or URLs.
class OwnerV2SessionService extends ChangeNotifier {
  OwnerV2SessionService({http.Client? client, String? baseUrl})
    : _client = client ?? http.Client(),
      _baseUrl = (baseUrl ?? assetForgeApiUrl).replaceFirst(RegExp(r'/$'), '');

  static final shared = OwnerV2SessionService();
  final http.Client _client;
  final String _baseUrl;
  String? _challenge;
  String? _proof;
  String? _token;
  Timer? _expiry;
  int _generation = 0;
  bool get authenticated => _token != null;

  Future<Map<String, dynamic>> _request(
    String path, {
    Map<String, String>? body,
    String? token,
    bool get = false,
  }) async {
    try {
      final uri = Uri.parse('$_baseUrl/auth/owner-v2/$path');
      final headers = <String, String>{
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };
      final response =
          await (get
                  ? _client.get(uri, headers: headers)
                  : _client.post(
                      uri,
                      headers: headers,
                      body: body == null ? null : jsonEncode(body),
                    ))
              .timeout(const Duration(seconds: 20));
      if (response.statusCode == 401) {
        throw const OwnerV2Exception('Session or code expired. Sign in again.');
      }
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw const OwnerV2Exception(
          'Owner sign-in is unavailable. Please retry.',
        );
      }
      if (response.statusCode == 204) return {};
      final decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) throw const FormatException();
      return decoded;
    } on OwnerV2Exception {
      rethrow;
    } catch (_) {
      // Never retry possibly consumed challenges or ambiguous revocations.
      throw const OwnerV2Exception(
        'Cannot confirm sign-in. Please start again.',
      );
    }
  }

  void clear() {
    _expiry?.cancel();
    _generation++;
    _challenge = null;
    _proof = null;
    _token = null;
    notifyListeners();
  }

  Future<void> requestCode(String email) async {
    clear();
    final generation = _generation;
    final result = await _request('request', body: {'email': email.trim()});
    if (generation != _generation) return;
    if (result['challenge_id'] is! String ||
        result['browser_proof'] is! String ||
        (result['browser_proof'] as String).length != 43) {
      throw const OwnerV2Exception('Invalid sign-in response.');
    }
    _challenge = result['challenge_id'] as String;
    _proof = result['browser_proof'] as String;
  }

  Future<void> verifyCode(String code) async {
    final challenge = _challenge;
    final proof = _proof;
    if (challenge == null || proof == null) {
      throw const OwnerV2Exception('Request a new email code first.');
    }
    final generation = _generation;
    // One attempt per local challenge. Ambiguous results require a new request.
    _challenge = null;
    _proof = null;
    final result = await _request(
      'verify',
      body: {
        'challenge_id': challenge,
        'browser_proof': proof,
        'code': code.trim(),
      },
    );
    if (generation != _generation) return;
    final token = result['session_token'];
    if (token is! String ||
        !RegExp(r'^sf_owner_v2_[A-Za-z0-9_-]{43}$').hasMatch(token) ||
        result['authenticated'] != true ||
        result['identity_version'] != 'owner_v2') {
      throw const OwnerV2Exception('Invalid sign-in response.');
    }
    _token = token;
    // SQL remains authoritative; local timeout only removes stale UI access.
    _expiry = Timer(const Duration(hours: 1), clear);
    notifyListeners();
  }

  Future<Map<String, String>> authorizationHeaders() async {
    final token = _token;
    final generation = _generation;
    if (token == null) {
      throw const OwnerV2Exception('Sign in with email to continue.');
    }
    try {
      final result = await _request('session', token: token, get: true);
      if (generation != _generation ||
          _token != token ||
          result['authenticated'] != true ||
          result['identity_version'] != 'owner_v2') {
        throw const OwnerV2Exception('Owner session changed. Sign in again.');
      }
      return {'Authorization': 'Bearer $token'};
    } catch (_) {
      if (generation == _generation) clear();
      rethrow;
    }
  }

  Future<void> logout() async {
    final token = _token;
    clear();
    if (token != null) await _request('logout', token: token);
  }

  @override
  void dispose() {
    _expiry?.cancel();
    _client.close();
    super.dispose();
  }
}

class OwnerV2Exception implements Exception {
  const OwnerV2Exception(this.message);
  final String message;
  @override
  String toString() => message;
}

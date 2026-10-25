import 'dart:convert';

import 'package:http/http.dart' as http;
import 'pollinations_session_service.dart';

class OwnerV2Exception implements Exception {
  const OwnerV2Exception(this.message);
  final String message;
  @override
  String toString() => message;
}

class OwnerV2Challenge {
  const OwnerV2Challenge(this.id, this.proof);
  final String id;
  final String proof;
}

/// V2 authentication never exchanges or trusts a legacy Supabase OAuth session.
/// Secrets are held only in memory and discarded on logout or app restart.
class OwnerV2SessionService {
  static final OwnerV2SessionService shared = OwnerV2SessionService();
  OwnerV2SessionService({http.Client? client, String? baseUrl})
      : _client = client ?? http.Client(),
        _baseUrl = (baseUrl ?? assetForgeApiUrl).replaceFirst(RegExp(r'/$'), '');

  final http.Client _client;
  final String _baseUrl;
  String? _token;

  bool get hasToken => _token != null;

  Future<Map<String, dynamic>> _call(String method, String path,
      {Map<String, dynamic>? body, String? token}) async {
    late http.Response response;
    try {
      final headers = <String, String>{
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };
      final uri = Uri.parse('$_baseUrl/auth/owner-v2/$path');
      response = method == 'GET'
          ? await _client.get(uri, headers: headers)
          : await _client.post(uri, headers: headers,
              body: body == null ? null : jsonEncode(body));
    } catch (_) {
      throw const OwnerV2Exception('Cannot reach SoloForge. Check the connection.');
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      if (response.statusCode == 401) {
        throw const OwnerV2Exception('Invalid or expired owner session/code.');
      }
      if (response.statusCode == 503) {
        throw const OwnerV2Exception('Owner V2 is not enabled or available on this server.');
      }
      throw OwnerV2Exception('Owner request failed (HTTP ${response.statusCode}).');
    }
    if (response.body.isEmpty) return <String, dynamic>{};
    try {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } catch (_) {
      throw const OwnerV2Exception('Invalid owner server response.');
    }
  }

  Future<OwnerV2Challenge> request(String email) async {
    final data = await _call('POST', 'request', body: {'email': email});
    final id = data['challenge_id'];
    final proof = data['browser_proof'];
    if (data['accepted'] != true || id is! String || proof is! String) {
      throw const OwnerV2Exception('Invalid challenge response.');
    }
    return OwnerV2Challenge(id, proof);
  }

  Future<void> verify(OwnerV2Challenge challenge, String code) async {
    final data = await _call('POST', 'verify', body: {
      'challenge_id': challenge.id,
      'browser_proof': challenge.proof,
      'code': code.trim(),
    });
    final token = data['session_token'];
    if (token is! String || !token.startsWith('sf_owner_v2_')) {
      throw const OwnerV2Exception('Invalid owner session response.');
    }
    // Verify the issued bearer against the server before granting app access.
    await _call('GET', 'session', token: token);
    _token = token;
  }

  Future<bool> restore() async {
    final token = _token;
    if (token == null) return false;
    try {
      await _call('GET', 'session', token: token);
      return true;
    } on OwnerV2Exception {
      _token = null;
      return false;
    }
  }

  Future<Map<String, String>> authorizationHeaders() async {
    if (!await restore()) throw const OwnerV2Exception('Sign in as the owner.');
    return {'Authorization': 'Bearer $_token'};
  }

  Future<void> logout() async {
    final token = _token;
    _token = null; // Fail closed locally even if server cannot be reached.
    if (token != null) await _call('POST', 'logout', token: token);
  }

  void dispose() => _client.close();
}

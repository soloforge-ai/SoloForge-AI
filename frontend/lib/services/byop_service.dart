import 'dart:convert';
import 'dart:typed_data';
import 'dart:math';
import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';
import 'pollinations_session_service.dart';
import 'soloforge_session_service.dart';

/// Uses existing Supabase/Owner V2 authentication. No new login/session authority.
class ByopService {
  static String newExecutionId() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
  }
  ByopService({required this.member, http.Client? client,
    Future<Map<String, String>> Function()? applicationAuthorization})
      : _client = client ?? http.Client(), _override = applicationAuthorization {
    connections = PollinationsSessionService(ownerAuthorization: applicationHeaders);
  }
  final bool member;
  final http.Client _client;
  final Future<Map<String, String>> Function()? _override;
  final _owner = SoloForgeSessionService(useOwnerV2: true);
  late final PollinationsSessionService connections;
  String? principal;
  String get _base => assetForgeApiUrl.replaceFirst(RegExp(r'/$'), '');

  Future<Map<String, String>> applicationHeaders() async {
    final override = _override;
    if (override != null) return override();
    if (!member) return _owner.authorizationHeaders();
    final auth = Supabase.instance.client.auth;
    final session = auth.currentSession;
    if (session == null || auth.currentUser == null || auth.currentUser!.isAnonymous) {
      throw const FormatException('Sign in with your registered Supabase account.');
    }
    return {'Authorization': 'Bearer ${session.accessToken}'};
  }

  Future<Map<String, String>> headers() async {
    final result = await applicationHeaders();
    final response = await _client.get(Uri.parse('$_base/v1/byop/session'), headers: result)
        .timeout(const Duration(seconds: 20));
    final data = decode(response);
    await _sameIdentity(result);
    final current = data['principal'] as String;
    if (!current.startsWith(member ? 'member:' : 'owner:') ||
        (principal != null && current != principal)) {
      throw const FormatException('Application identity changed. Reopen BYOP.');
    }
    principal = current;
    return result;
  }

  Map<String, dynamic> decode(http.Response response) {
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw FormatException(data['detail']?.toString() ?? 'BYOP request failed.');
    }
    return data;
  }

  Future<void> _sameIdentity(Map<String, String> before) async {
    if ((await applicationHeaders())['Authorization'] != before['Authorization']) {
      throw const FormatException('Identity changed while the request was in flight. Do not replay a mutation.');
    }
  }

  Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body) async {
    final auth = await headers();
    final response = await _client.post(Uri.parse('$_base/v1/byop/$path'),
        headers: {...auth, 'Content-Type': 'application/json'}, body: jsonEncode(body))
        .timeout(const Duration(minutes: 6));
    await _sameIdentity(auth);
    return decode(response);
  }

  Future<Map<String, dynamic>> get(String path) async {
    final auth = await headers();
    final response = await _client.get(Uri.parse('$_base/v1/byop/$path'), headers: auth)
        .timeout(const Duration(seconds: 30));
    await _sameIdentity(auth);
    return decode(response);
  }

  Future<Uint8List> image(String jobId, String expectedSha) async {
    final auth = await headers();
    final response = await _client.get(Uri.parse('$_base/v1/byop/jobs/$jobId/asset'), headers: auth)
        .timeout(const Duration(seconds: 30));
    await _sameIdentity(auth);
    if (response.statusCode != 200) decode(response);
    if (sha256.convert(response.bodyBytes).toString() != expectedSha) {
      throw const FormatException('Preview does not match the current image.');
    }
    return response.bodyBytes;
  }

  Future<Map<String, dynamic>> review(String jobId, Uint8List displayedImage, bool approved) =>
      post('jobs/$jobId/asset-review', {'decision': approved ? 'APPROVED' : 'REJECTED',
        'asset_sha256': sha256.convert(displayedImage).toString()});

  Future<Map<String, dynamic>> audio(String jobId, Uint8List wav) async {
    final auth = await headers();
    final response = await _client.post(Uri.parse('$_base/v1/byop/jobs/$jobId/audio'),
        headers: {...auth, 'Content-Type': 'audio/wav'}, body: wav)
        .timeout(const Duration(seconds: 60));
    await _sameIdentity(auth);
    return decode(response);
  }

  void dispose() {
    _client.close();
    connections.dispose();
    _owner.dispose();
  }
}

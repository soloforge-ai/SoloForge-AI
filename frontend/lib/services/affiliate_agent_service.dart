import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../models/affiliate_content_package.dart';
import '../models/affiliate_program.dart';
import 'pollinations_session_service.dart';

class AffiliateAgentService {
  AffiliateAgentService({
    http.Client? client,
    FlutterSecureStorage? storage,
  })  : _client = client ?? http.Client(),
        _storage = storage ?? const FlutterSecureStorage();

  static const _savedKey = 'affiliate_agent_saved_programs_v01';

  final http.Client _client;
  final FlutterSecureStorage _storage;

  String get _baseUrl =>
      assetForgeApiUrl.trim().replaceFirst(RegExp(r'/$'), '');

  Future<List<AffiliateProgram>> searchPrograms({
    String query = '',
    bool recurringOnly = false,
    bool verifiedOnly = false,
    int? minCookieDays,
    int limit = 50,
  }) async {
    final params = <String, String>{
      if (query.trim().isNotEmpty) 'q': query.trim(),
      if (recurringOnly) 'type': 'recurring',
      if (verifiedOnly) 'verified': 'true',
      if (minCookieDays != null && minCookieDays > 0)
        'min_cookie_days': '$minCookieDays',
      'limit': '$limit',
    };

    final uri = Uri.parse('$_baseUrl/v1/affiliate/programs').replace(
      queryParameters: params,
    );
    final response = await _client.get(uri);
    _ensureSuccess(response);

    final body = jsonDecode(response.body);
    if (body is! List) {
      throw const AffiliateAgentException(
        'Affiliate discovery returned an invalid response.',
      );
    }

    return body
        .whereType<Map>()
        .map((row) => AffiliateProgram.fromJson(
              row.map((key, value) => MapEntry(key.toString(), value)),
            ))
        .where((program) => program.slug.isNotEmpty && program.name.isNotEmpty)
        .toList(growable: false);
  }

  Future<AffiliateOpportunityScore> analyzeProgram({
    required String slug,
    required String niche,
    required String audience,
  }) async {
    final safeSlug = Uri.encodeComponent(slug);
    final response = await _client.post(
      Uri.parse('$_baseUrl/v1/affiliate/programs/$safeSlug/analyze'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({
        'niche': niche.trim(),
        'audience': audience.trim(),
      }),
    );
    _ensureSuccess(response);

    final body = jsonDecode(response.body);
    if (body is! Map) {
      throw const AffiliateAgentException(
        'Affiliate analysis returned an invalid response.',
      );
    }
    return AffiliateOpportunityScore.fromJson(
      body.map((key, value) => MapEntry(key.toString(), value)),
    );
  }

  Future<AffiliateContentPackage> generateContentPackage({
    required String slug,
    required String platform,
    required String format,
    required String intent,
    required String goal,
    required String niche,
    required String audience,
    String language = 'th',
    String? affiliateUrl,
  }) async {
    final session = PollinationsSessionService();
    Map<String, String> authHeaders;
    try {
      authHeaders = await session.authorizationHeaders();
    } on PollinationsSessionException {
      throw const AffiliateAgentException(
        'Connect Pollinations before generating AI content.',
      );
    } finally {
      await session.dispose();
    }

    final response = await _client.post(
      Uri.parse('$_baseUrl/v1/affiliate/content/generate'),
      headers: {
        ...authHeaders,
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'slug': slug,
        'platform': platform,
        'format': format,
        'intent': intent,
        'goal': goal,
        'niche': niche.trim(),
        'audience': audience.trim(),
        'language': language,
        if (affiliateUrl != null && affiliateUrl.trim().isNotEmpty)
          'affiliate_url': affiliateUrl.trim(),
      }),
    );
    _ensureSuccess(response);

    final body = jsonDecode(response.body);
    if (body is! Map) {
      throw const AffiliateAgentException(
        'Content Factory returned an invalid response.',
      );
    }
    return AffiliateContentPackage.fromJson(
      body.map((key, value) => MapEntry(key.toString(), value)),
    );
  }

  Future<List<AffiliateProgram>> readSavedPrograms() async {
    final raw = await _storage.read(key: _savedKey);
    if (raw == null || raw.trim().isEmpty) return const [];

    try {
      final body = jsonDecode(raw);
      if (body is! List) return const [];
      return body
          .whereType<Map>()
          .map((row) => AffiliateProgram.fromJson(
                row.map((key, value) => MapEntry(key.toString(), value)),
              ))
          .where((program) => program.slug.isNotEmpty)
          .toList(growable: false);
    } catch (_) {
      return const [];
    }
  }

  Future<void> saveProgram(AffiliateProgram program) async {
    final current = await readSavedPrograms();
    final bySlug = <String, AffiliateProgram>{
      for (final item in current) item.slug: item,
      program.slug: program,
    };
    await _storage.write(
      key: _savedKey,
      value: jsonEncode(bySlug.values.map((item) => item.toJson()).toList()),
    );
  }

  Future<void> removeSavedProgram(String slug) async {
    final current = await readSavedPrograms();
    final next = current.where((item) => item.slug != slug).toList();
    await _storage.write(
      key: _savedKey,
      value: jsonEncode(next.map((item) => item.toJson()).toList()),
    );
  }

  void dispose() => _client.close();

  void _ensureSuccess(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) return;

    var message = 'Affiliate Agent request failed (${response.statusCode}).';
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['detail'] != null) {
        message = body['detail'].toString();
      }
    } catch (_) {}
    throw AffiliateAgentException(message);
  }
}

class AffiliateAgentException implements Exception {
  const AffiliateAgentException(this.message);

  final String message;

  @override
  String toString() => message;
}

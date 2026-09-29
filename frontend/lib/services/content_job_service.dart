import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/content_job.dart';
import 'pollinations_session_service.dart';

class PublishingConnection {
  const PublishingConnection({
    required this.platformId,
    required this.username,
    required this.connectionStatus,
    required this.tokenStatus,
  });

  final String platformId;
  final String username;
  final String connectionStatus;
  final String tokenStatus;

  String get platform => platformId.split('-').first;

  factory PublishingConnection.fromJson(Map<String, dynamic> json) {
    return PublishingConnection(
      platformId: json['platformId']?.toString() ?? '',
      username: json['username']?.toString() ?? '',
      connectionStatus: json['connectionStatus']?.toString() ?? '',
      tokenStatus: json['tokenStatus']?.toString() ?? '',
    );
  }
}

class ContentAnalyticsSummary {
  const ContentAnalyticsSummary({
    required this.jobsTotal,
    required this.published,
    required this.failed,
    required this.review,
    required this.averageScore,
    required this.averageGenerationSeconds,
    required this.averageTimeToPublishSeconds,
    required this.byStatus,
    required this.byPlatform,
    required this.performanceSnapshots,
    required this.performanceAvailable,
  });

  final int jobsTotal;
  final int published;
  final int failed;
  final int review;
  final double? averageScore;
  final double? averageGenerationSeconds;
  final double? averageTimeToPublishSeconds;
  final Map<String, int> byStatus;
  final Map<String, int> byPlatform;
  final int performanceSnapshots;
  final bool performanceAvailable;

  factory ContentAnalyticsSummary.fromJson(Map<String, dynamic> json) {
    Map<String, int> intMap(dynamic raw) {
      if (raw is! Map) return const {};
      return raw.map(
        (key, value) => MapEntry(
          key.toString(),
          value is num ? value.toInt() : int.tryParse(value.toString()) ?? 0,
        ),
      );
    }

    double? asDouble(dynamic value) {
      if (value == null) return null;
      if (value is num) return value.toDouble();
      return double.tryParse(value.toString());
    }

    return ContentAnalyticsSummary(
      jobsTotal: (json['jobs_total'] as num?)?.toInt() ?? 0,
      published: (json['published'] as num?)?.toInt() ?? 0,
      failed: (json['failed'] as num?)?.toInt() ?? 0,
      review: (json['review'] as num?)?.toInt() ?? 0,
      averageScore: asDouble(json['average_score']),
      averageGenerationSeconds: asDouble(json['average_generation_seconds']),
      averageTimeToPublishSeconds:
          asDouble(json['average_time_to_publish_seconds']),
      byStatus: intMap(json['by_status']),
      byPlatform: intMap(json['by_platform']),
      performanceSnapshots:
          (json['performance_snapshots'] as num?)?.toInt() ?? 0,
      performanceAvailable: json['performance_available'] == true,
    );
  }
}

class ContentJobService {
  ContentJobService({
    http.Client? client,
    PollinationsSessionService? sessionService,
  })  : _client = client ?? http.Client(),
        _sessionService = sessionService ?? PollinationsSessionService();

  final http.Client _client;
  final PollinationsSessionService _sessionService;

  String get _baseUrl =>
      assetForgeApiUrl.trim().replaceFirst(RegExp(r'/$'), '');

  Future<Map<String, String>> _headers({bool json = false}) async {
    final headers = await _sessionService.authorizationHeaders();
    if (json) {
      headers['Content-Type'] = 'application/json';
    }
    return headers;
  }

  Never _throwFor(http.Response response, String action) {
    if (response.statusCode == 401) {
      throw const ContentJobAuthException();
    }
    String detail = '';
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['detail'] != null) {
        detail = body['detail'].toString();
      }
    } catch (_) {}
    throw Exception(
      detail.isEmpty ? '$action returned ${response.statusCode}.' : detail,
    );
  }

  ContentJob _decodeJob(http.Response response) {
    return ContentJob.fromJson(
      (jsonDecode(response.body) as Map).map(
        (key, value) => MapEntry(key.toString(), value),
      ),
    );
  }

  Future<List<ContentJob>> getJobs({int limit = 100}) async {
    final response = await _client
        .get(
          Uri.parse('$_baseUrl/v1/content-jobs?limit=$limit'),
          headers: await _headers(),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Content queue');
    }

    final body = jsonDecode(response.body);
    final items = body is List
        ? body
        : (body is Map<String, dynamic> ? body['items'] as List<dynamic>? : null);
    if (items == null) return const [];

    return items
        .whereType<Map>()
        .map((row) => ContentJob.fromJson(
              row.map((key, value) => MapEntry(key.toString(), value)),
            ))
        .toList();
  }

  Future<ContentAnalyticsSummary> getAnalyticsSummary() async {
    final response = await _client
        .get(
          Uri.parse('$_baseUrl/v1/analytics/summary'),
          headers: await _headers(),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Analytics summary');
    }

    final body = jsonDecode(response.body);
    if (body is! Map) {
      throw Exception('Analytics summary returned an invalid response.');
    }
    return ContentAnalyticsSummary.fromJson(
      body.map((key, value) => MapEntry(key.toString(), value)),
    );
  }

  Future<ContentJob> getJob(String id) async {
    final response = await _client
        .get(
          Uri.parse('$_baseUrl/v1/content-jobs/$id'),
          headers: await _headers(),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Content job');
    }
    return _decodeJob(response);
  }

  Future<ContentJob> updateDraft(
    String id, {
    required String hook,
    required String script,
    required String caption,
    required String cta,
    required String visualPrompt,
    required String motionPrompt,
  }) async {
    final response = await _client
        .patch(
          Uri.parse('$_baseUrl/v1/content-jobs/$id/draft'),
          headers: await _headers(json: true),
          body: jsonEncode({
            'hook': hook,
            'script': script,
            'caption': caption,
            'cta': cta,
            'visual_prompt': visualPrompt,
            'motion_prompt': motionPrompt,
          }),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Save draft');
    }
    return _decodeJob(response);
  }

  Future<ContentJob> approve(String id) async {
    final response = await _client
        .post(
          Uri.parse('$_baseUrl/v1/content-jobs/$id/approve'),
          headers: await _headers(),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Approve');
    }
    return _decodeJob(response);
  }

  Future<List<PublishingConnection>> getPublishingConnections() async {
    final response = await _client
        .get(
          Uri.parse('$_baseUrl/v1/publishing/connections'),
          headers: await _headers(),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Publishing connections');
    }
    final body = jsonDecode(response.body);
    final items = body is Map ? body['items'] as List<dynamic>? : null;
    if (items == null) return const [];
    return items
        .whereType<Map>()
        .map((row) => PublishingConnection.fromJson(
              row.map((key, value) => MapEntry(key.toString(), value)),
            ))
        .where((item) => item.platformId.isNotEmpty)
        .toList();
  }

  Future<ContentJob> publishNow(
    String id, {
    required List<String> platformIds,
  }) async {
    final response = await _client
        .post(
          Uri.parse('$_baseUrl/v1/publishing/$id/publish-now'),
          headers: await _headers(json: true),
          body: jsonEncode({'platform_ids': platformIds}),
        )
        .timeout(const Duration(seconds: 45));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Publish now');
    }
    return _decodeJob(response);
  }

  Future<ContentJob> schedule(
    String id, {
    required List<String> platformIds,
    required DateTime scheduledTime,
  }) async {
    final response = await _client
        .post(
          Uri.parse('$_baseUrl/v1/publishing/$id/schedule'),
          headers: await _headers(json: true),
          body: jsonEncode({
            'platform_ids': platformIds,
            'scheduled_time': scheduledTime.toUtc().toIso8601String(),
          }),
        )
        .timeout(const Duration(seconds: 45));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Schedule');
    }
    return _decodeJob(response);
  }

  Future<ContentJob> regenerate(String id) async {
    final response = await _client
        .post(
          Uri.parse('$_baseUrl/v1/content-jobs/$id/regenerate'),
          headers: await _headers(),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Regenerate');
    }
    return _decodeJob(response);
  }
}

class ContentJobAuthException implements Exception {
  const ContentJobAuthException();

  @override
  String toString() =>
      'Connect Pollinations once in SoloForge before opening the private content queue.';
}

import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/content_job.dart';
import 'pollinations_session_service.dart';

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

  Future<List<ContentJob>> getJobs({int limit = 100}) async {
    final headers = await _sessionService.authorizationHeaders();
    final response = await _client
        .get(
          Uri.parse('$_baseUrl/v1/content-jobs?limit=$limit'),
          headers: headers,
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode == 401) {
      throw const ContentJobAuthException();
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Content queue returned ${response.statusCode}.');
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

  Future<ContentJob> getJob(String id) async {
    final headers = await _sessionService.authorizationHeaders();
    final response = await _client
        .get(Uri.parse('$_baseUrl/v1/content-jobs/$id'), headers: headers)
        .timeout(const Duration(seconds: 30));

    if (response.statusCode == 401) {
      throw const ContentJobAuthException();
    }
    if (response.statusCode == 404) {
      throw Exception('Content job not found.');
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Content job returned ${response.statusCode}.');
    }

    return ContentJob.fromJson(
      (jsonDecode(response.body) as Map).map(
        (key, value) => MapEntry(key.toString(), value),
      ),
    );
  }
}

class ContentJobAuthException implements Exception {
  const ContentJobAuthException();

  @override
  String toString() =>
      'Connect Pollinations once in SoloForge before opening the private content queue.';
}

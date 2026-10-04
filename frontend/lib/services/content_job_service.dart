import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/content_job.dart';
import 'pollinations_session_service.dart';
import 'soloforge_session_service.dart';

class IdeaRecommendation {
  const IdeaRecommendation({
    required this.id,
    required this.title,
    required this.rank,
    required this.fitScore,
    required this.recommended,
    required this.platforms,
    required this.goal,
    required this.needsVideo,
    required this.hookDirection,
    required this.productionDifficulty,
    required this.reason,
  });

  final String id;
  final String title;
  final int rank;
  final int fitScore;
  final bool recommended;
  final List<String> platforms;
  final String goal;
  final bool needsVideo;
  final String hookDirection;
  final String productionDifficulty;
  final String reason;

  factory IdeaRecommendation.fromJson(Map<String, dynamic> json) {
    final rawPlatforms = json['platforms'];
    return IdeaRecommendation(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      rank: (json['rank'] as num?)?.toInt() ?? 0,
      fitScore: (json['fit_score'] as num?)?.toInt() ?? 0,
      recommended: json['recommended'] == true,
      platforms: rawPlatforms is List
          ? rawPlatforms.map((value) => value.toString()).toList()
          : const [],
      goal: json['goal']?.toString() ?? '',
      needsVideo: json['needs_video'] == true,
      hookDirection: json['hook_direction']?.toString() ?? '',
      productionDifficulty:
          json['production_difficulty']?.toString() ?? '',
      reason: json['reason']?.toString() ?? '',
    );
  }
}

class IdeaAnalysis {
  const IdeaAnalysis({
    required this.idea,
    required this.recommendedFormat,
    required this.options,
    required this.minibossScore,
    required this.minibossDecision,
  });

  final String idea;
  final String recommendedFormat;
  final List<IdeaRecommendation> options;
  final int minibossScore;
  final String minibossDecision;

  factory IdeaAnalysis.fromJson(Map<String, dynamic> json) {
    final rawOptions = json['options'];
    final rawMiniBoss = json['miniboss'];
    final miniboss = rawMiniBoss is Map
        ? rawMiniBoss.map((key, value) => MapEntry(key.toString(), value))
        : const <String, dynamic>{};

    return IdeaAnalysis(
      idea: json['idea']?.toString() ?? '',
      recommendedFormat: json['recommended_format']?.toString() ?? '',
      options: rawOptions is List
          ? rawOptions
              .whereType<Map>()
              .map((row) => IdeaRecommendation.fromJson(
                    row.map(
                      (key, value) => MapEntry(key.toString(), value),
                    ),
                  ))
              .toList()
          : const [],
      minibossScore: (miniboss['score'] as num?)?.toInt() ?? 0,
      minibossDecision: miniboss['decision']?.toString() ?? '',
    );
  }
}

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

class AnalyticsProviderCapability {
  const AnalyticsProviderCapability({
    required this.provider,
    required this.platform,
    required this.username,
    required this.connectionStatus,
    required this.metadataSync,
    required this.engagementMetrics,
  });

  final String provider;
  final String platform;
  final String username;
  final String connectionStatus;
  final bool metadataSync;
  final bool? engagementMetrics;

  factory AnalyticsProviderCapability.fromJson(Map<String, dynamic> json) {
    return AnalyticsProviderCapability(
      provider: json['provider']?.toString() ?? '',
      platform: json['platform']?.toString() ?? '',
      username: json['username']?.toString() ?? '',
      connectionStatus: json['connection_status']?.toString() ?? '',
      metadataSync: json['metadata_sync'] == true,
      engagementMetrics: json['engagement_metrics'] is bool
          ? json['engagement_metrics'] as bool
          : null,
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
    required this.latestSeries,
    required this.totalViews,
    required this.totalInteractions,
    required this.engagementRatePercent,
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
  final int latestSeries;
  final int totalViews;
  final int totalInteractions;
  final double? engagementRatePercent;

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
      latestSeries: (json['latest_series'] as num?)?.toInt() ?? 0,
      totalViews: (json['total_views'] as num?)?.toInt() ?? 0,
      totalInteractions: (json['total_interactions'] as num?)?.toInt() ?? 0,
      engagementRatePercent: asDouble(json['engagement_rate_percent']),
    );
  }
}

class ContentFeedback {
  const ContentFeedback({
    required this.state,
    required this.sampleSize,
    required this.minimumSampleSize,
    required this.scoreAdjustment,
    required this.automationAction,
    required this.reasons,
  });

  final String state;
  final int sampleSize;
  final int minimumSampleSize;
  final int scoreAdjustment;
  final String automationAction;
  final List<String> reasons;

  factory ContentFeedback.fromJson(Map<String, dynamic> json) {
    final rawReasons = json['reasons'];
    return ContentFeedback(
      state: json['state']?.toString() ?? 'INSUFFICIENT_DATA',
      sampleSize: (json['sample_size'] as num?)?.toInt() ?? 0,
      minimumSampleSize:
          (json['minimum_sample_size'] as num?)?.toInt() ?? 0,
      scoreAdjustment: (json['score_adjustment'] as num?)?.toInt() ?? 0,
      automationAction:
          json['automation_action']?.toString() ?? 'COLLECT_MORE_DATA',
      reasons: rawReasons is List
          ? rawReasons.map((value) => value.toString()).toList()
          : const [],
    );
  }
}

class ContentAssetPreview {
  const ContentAssetPreview({
    required this.url,
    required this.mediaType,
    required this.assetStatus,
    required this.pipelineRoute,
  });

  final String url;
  final String mediaType;
  final String? assetStatus;
  final String? pipelineRoute;

  factory ContentAssetPreview.fromJson(Map<String, dynamic> json) {
    return ContentAssetPreview(
      url: json['url']?.toString() ?? '',
      mediaType: json['media_type']?.toString() ?? 'image',
      assetStatus: json['asset_status']?.toString(),
      pipelineRoute: json['pipeline_route']?.toString(),
    );
  }
}

class ContentJobService {
  ContentJobService({
    http.Client? client,
    SoloForgeSessionService? sessionService,
  })  : _client = client ?? http.Client(),
        _sessionService = sessionService ?? SoloForgeSessionService();

  final http.Client _client;
  final SoloForgeSessionService _sessionService;

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


  Future<IdeaAnalysis> analyzeIdea(String idea) async {
    final response = await _client
        .post(
          Uri.parse('$_baseUrl/v1/content-jobs/idea/analyze'),
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode({'idea': idea}),
        )
        .timeout(const Duration(seconds: 20));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Analyze idea');
    }
    final body = jsonDecode(response.body);
    if (body is! Map) {
      throw Exception('Idea analysis returned an invalid response.');
    }
    return IdeaAnalysis.fromJson(
      body.map((key, value) => MapEntry(key.toString(), value)),
    );
  }

  Future<ContentJob> createFromIdea({
    required String idea,
    required String recommendationId,
    required bool generateNow,
  }) async {
    final response = await _client
        .post(
          Uri.parse('$_baseUrl/v1/content-jobs/idea/create'),
          headers: await _headers(json: true),
          body: jsonEncode({
            'idea': idea,
            'recommendation_id': recommendationId,
            'action': generateNow ? 'generate' : 'save',
          }),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, generateNow ? 'Generate idea' : 'Save idea');
    }
    return _decodeJob(response);
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

  Future<Map<String, dynamic>> cancelJob(String id) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/v1/content-jobs/$id/cancel'),
      headers: await _headers(),
    ).timeout(const Duration(seconds: 30));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Cancel job');
    }
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> resetQueue() async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/v1/content-jobs/queue/reset'),
      headers: await _headers(),
    ).timeout(const Duration(seconds: 60));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Reset queue');
    }
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
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

  Future<List<AnalyticsProviderCapability>> getAnalyticsProviders() async {
    final response = await _client
        .get(
          Uri.parse('$_baseUrl/v1/analytics/providers'),
          headers: await _headers(),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Analytics providers');
    }

    final body = jsonDecode(response.body);
    final items = body is Map ? body['items'] as List<dynamic>? : null;
    if (items == null) return const [];
    return items
        .whereType<Map>()
        .map((row) => AnalyticsProviderCapability.fromJson(
              row.map((key, value) => MapEntry(key.toString(), value)),
            ))
        .toList();
  }

  Future<ContentFeedback> getPerformanceFeedback(String id) async {
    final response = await _client
        .get(
          Uri.parse('$_baseUrl/v1/analytics/jobs/$id/feedback'),
          headers: await _headers(),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Performance feedback');
    }
    final body = jsonDecode(response.body);
    if (body is! Map) {
      throw Exception('Performance feedback returned an invalid response.');
    }
    return ContentFeedback.fromJson(
      body.map((key, value) => MapEntry(key.toString(), value)),
    );
  }

  Future<ContentAssetPreview> getAssetPreview(String id) async {
    final response = await _client
        .get(
          Uri.parse('$_baseUrl/v1/content-jobs/$id/asset-preview'),
          headers: await _headers(),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      _throwFor(response, 'Asset preview');
    }

    final body = jsonDecode(response.body);
    if (body is! Map) {
      throw Exception('Asset preview returned an invalid response.');
    }
    final preview = ContentAssetPreview.fromJson(
      body.map((key, value) => MapEntry(key.toString(), value)),
    );
    if (preview.url.trim().isEmpty) {
      throw Exception('Asset preview did not return a media URL.');
    }
    return preview;
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

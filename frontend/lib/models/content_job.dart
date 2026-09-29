class ContentJob {
  const ContentJob({
    required this.id,
    required this.idea,
    required this.status,
    required this.publishPlatform,
    required this.publishStatus,
    required this.contentPackage,
    this.score,
    this.scoreReason,
    this.hook,
    this.script,
    this.caption,
    this.cta,
    this.visualPrompt,
    this.motionPrompt,
    this.riskLevel,
    this.qaStatus,
    this.generatorProvider,
    this.generatorModel,
    this.publoraPostId,
    this.publishedAt,
    this.videoStoragePath,
    this.generatedAt,
    this.createdAt,
    this.updatedAt,
  });

  final String id;
  final String idea;
  final String status;
  final double? score;
  final String? scoreReason;
  final String? hook;
  final String? script;
  final String? caption;
  final String? cta;
  final String? visualPrompt;
  final String? motionPrompt;
  final String? riskLevel;
  final String? qaStatus;
  final String publishPlatform;
  final String publishStatus;
  final String? generatorProvider;
  final String? generatorModel;
  final String? publoraPostId;
  final DateTime? publishedAt;
  final String? videoStoragePath;
  final DateTime? generatedAt;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final Map<String, dynamic> contentPackage;

  String get contentId =>
      contentPackage['content_id']?.toString().trim().isNotEmpty == true
          ? contentPackage['content_id'].toString()
          : id.substring(0, id.length < 8 ? id.length : 8).toUpperCase();

  String get format => contentPackage['format']?.toString() ?? 'content';
  String get goal => contentPackage['goal']?.toString() ?? '-';
  String get priority => contentPackage['priority']?.toString() ?? 'MEDIUM';
  bool get needsVideo => contentPackage['needs_video'] == true;
  String get pipelineRoute =>
      contentPackage['pipeline_route']?.toString() ?? '-';
  String get assetStatus =>
      contentPackage['asset_status']?.toString() ?? '-';
  String? get assetStoragePath =>
      contentPackage['asset_storage_path']?.toString();
  DateTime? get scheduledTime =>
      _asDate(contentPackage['scheduled_time']);

  DateTime? get plannedDate {
    final value = contentPackage['planned_date']?.toString();
    if (value == null || value.isEmpty) return null;
    return DateTime.tryParse(value);
  }

  String? get blocker {
    final explicit = contentPackage['blocker']?.toString();
    if (explicit != null && explicit.trim().isNotEmpty) return explicit.trim();
    if (status == 'GENERATION_FAILED') return 'Generation failed';
    if (status == 'ASSET_FAILED') return 'Asset generation failed';
    if (status == 'AUDIO_FAILED') return 'Audio generation failed';
    if (status == 'RENDER_FAILED') return 'Render failed';
    if (status == 'PUBLISH_FAILED') return 'Publish failed';
    if (needsVideo && status == 'BACKLOG') return 'Waiting for video pipeline';
    return null;
  }

  factory ContentJob.fromJson(Map<String, dynamic> json) {
    final rawPackage = json['content_package'];
    return ContentJob(
      id: json['id']?.toString() ?? '',
      idea: json['idea']?.toString() ?? '',
      status: json['status']?.toString() ?? 'NEW',
      score: _asDouble(json['score']),
      scoreReason: json['score_reason']?.toString(),
      hook: json['hook']?.toString(),
      script: json['script']?.toString(),
      caption: json['caption']?.toString(),
      cta: json['cta']?.toString(),
      visualPrompt: json['visual_prompt']?.toString(),
      motionPrompt: json['motion_prompt']?.toString(),
      riskLevel: json['risk_level']?.toString(),
      qaStatus: json['qa_status']?.toString(),
      publishPlatform: json['publish_platform']?.toString() ?? '-',
      publishStatus: json['publish_status']?.toString() ?? 'PENDING',
      generatorProvider: json['generator_provider']?.toString(),
      generatorModel: json['generator_model']?.toString(),
      publoraPostId: json['publora_post_id']?.toString(),
      publishedAt: _asDate(json['published_at']),
      videoStoragePath: json['video_storage_path']?.toString(),
      generatedAt: _asDate(json['generated_at']),
      createdAt: _asDate(json['created_at']),
      updatedAt: _asDate(json['updated_at']),
      contentPackage: rawPackage is Map<String, dynamic>
          ? rawPackage
          : rawPackage is Map
              ? rawPackage.map((key, value) => MapEntry(key.toString(), value))
              : const <String, dynamic>{},
    );
  }

  static double? _asDouble(dynamic value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString());
  }

  static DateTime? _asDate(dynamic value) {
    if (value == null) return null;
    return DateTime.tryParse(value.toString());
  }
}

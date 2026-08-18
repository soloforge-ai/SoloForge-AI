enum AiModelModality {
  text,
  image,
  video,
  audio,
  embedding,
  threeD,
  realtime,
  unknown,
}

class AiModel {
  final String id;
  final String name;
  final String provider;
  final bool community;
  final Set<AiModelModality> modalities;
  final Map<String, dynamic> capabilities;
  final Map<String, dynamic> pricing;
  final Map<String, dynamic> raw;

  const AiModel({
    required this.id,
    required this.name,
    required this.provider,
    required this.community,
    required this.modalities,
    required this.capabilities,
    required this.pricing,
    required this.raw,
  });

  bool supports(AiModelModality modality) => modalities.contains(modality);

  factory AiModel.fromJson(Map<String, dynamic> json) {
    final id = '${json['id'] ?? ''}';
    final type = '${json['type'] ?? ''}'.toLowerCase();
    final modalityValues = <String>[
      if (json['modality'] != null) '${json['modality']}',
      if (json['modalities'] is List) ...List<dynamic>.from(json['modalities']),
      if (type.isNotEmpty) type,
    ];

    final modalities = modalityValues
        .expand((value) => value.split(RegExp(r'[,/ ]+')))
        .map(_parseModality)
        .where((value) => value != AiModelModality.unknown)
        .toSet();

    return AiModel(
      id: id,
      name: '${json['name'] ?? id}',
      provider: '${json['provider'] ?? _providerFromId(id)}',
      community: json['community'] == true || id.contains('/'),
      modalities: modalities.isEmpty ? {AiModelModality.unknown} : modalities,
      capabilities: _map(json['capabilities']),
      pricing: _map(json['pricing'] ?? json['price']),
      raw: Map<String, dynamic>.from(json),
    );
  }

  static Map<String, dynamic> _map(dynamic value) =>
      value is Map ? Map<String, dynamic>.from(value) : <String, dynamic>{};

  static String _providerFromId(String id) {
    if (id.contains('/')) return id.split('/').first;
    return id.split(RegExp(r'[-:]')).first;
  }

  static AiModelModality _parseModality(String value) {
    final v = value.toLowerCase().replaceAll('_', '-');
    if (v.contains('text') || v.contains('chat')) return AiModelModality.text;
    if (v.contains('image')) return AiModelModality.image;
    if (v.contains('video')) return AiModelModality.video;
    if (v.contains('audio') || v.contains('speech')) return AiModelModality.audio;
    if (v.contains('embedding')) return AiModelModality.embedding;
    if (v == '3d' || v.contains('three')) return AiModelModality.threeD;
    if (v.contains('realtime')) return AiModelModality.realtime;
    return AiModelModality.unknown;
  }
}

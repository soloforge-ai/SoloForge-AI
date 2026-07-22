class Character {
  final String id;
  final String version;

  final String name;
  final String role;
  final String description;

  final double heightCm;
  final String style;

  final Map<String, String> references;

  final String basePrompt;
  final String negativePrompt;

  const Character({
    required this.id,
    required this.version,
    required this.name,
    required this.role,
    required this.description,
    required this.heightCm,
    required this.style,
    required this.references,
    required this.basePrompt,
    required this.negativePrompt,
  });

  factory Character.fromJson(Map<String, dynamic> json) {
    return Character(
      id: json['id'],
      version: json['version'],

      name: json['name'],
      role: json['role'],
      description: json['description'],

      heightCm:
          (json['physical']['height_cm'] as num).toDouble(),

      style: json['physical']['style'],

      references:
          Map<String, String>.from(json['references']),

      basePrompt:
          json['prompt']['base'],

      negativePrompt:
          json['prompt']['negative'],
    );
  }

  String? reference(String key) {
    return references[key];
  }
}
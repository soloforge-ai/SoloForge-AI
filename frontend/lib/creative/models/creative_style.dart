class CreativeStyle {
  final String id;
  final String name;
  final String description;

  final Map<String, dynamic> prompt;
  final List<dynamic> negativePrompt;

  CreativeStyle({
    required this.id,
    required this.name,
    required this.description,
    required this.prompt,
    required this.negativePrompt,
  });

  factory CreativeStyle.fromJson(Map<String, dynamic> json) {
    return CreativeStyle(
      id: json["id"],
      name: json["name"],
      description: json["description"],
      prompt: Map<String, dynamic>.from(json["prompt"]),
      negativePrompt: List<dynamic>.from(json["negative_prompt"]),
    );
  }
}
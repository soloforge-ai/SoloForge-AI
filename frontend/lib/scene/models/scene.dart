class Scene {
  final String id;
  final String name;
  final String description;

  final Map<String, dynamic> prompt;

  Scene({
    required this.id,
    required this.name,
    required this.description,
    required this.prompt,
  });

  factory Scene.fromJson(Map<String, dynamic> json) {
    return Scene(
      id: json["id"],
      name: json["name"],
      description: json["description"],
      prompt: Map<String, dynamic>.from(json["prompt"]),
    );
  }
}
/// Mirrors the Asset Forge API layout contract; legacy callers default to sheets.
class AssetForgeGenerationConfig {
  const AssetForgeGenerationConfig({
    this.layout = 'sticker_sheet',
    this.pose = 'presenting',
    this.expression = 'calm',
    this.wardrobe = 'default',
    this.campaign,
  });

  final String layout;
  final String pose;
  final String expression;
  final String wardrobe;
  final String? campaign;

  bool get isSingle => layout == 'single_character';
  int get quantity => isSingle ? 1 : 4;
  static const poses = ['presenting', 'pointing', 'thinking', 'standing'];
  static const wardrobes = ['default', 'creator', 'fitness', 'casual', 'formal_black'];
  static List<String> expressionsFor(String pose) =>
      pose == 'thinking' ? ['calm', 'thoughtful'] : ['calm', 'subtle_smile'];

  Map<String, dynamic> requestFields(List<String> messages) {
    if (!['sticker_sheet', 'single_character'].contains(layout) ||
        !poses.contains(pose) || !expressionsFor(pose).contains(expression) ||
        !wardrobes.contains(wardrobe)) {
      throw ArgumentError('Invalid generation layout, pose, expression or wardrobe');
    }
    if (isSingle && messages.isNotEmpty) {
      throw ArgumentError('Single-character mode uses one pose and expression, not messages');
    }
    return {
      'generation_layout': layout,
      'quantity': quantity,
      'messages': messages,
      'wardrobe_variant': wardrobe,
      'campaign_id': campaign,
      if (isSingle) 'pose_intent': pose,
      if (isSingle) 'expression': expression,
      if (isSingle) 'framing': 'full_figure',
    };
  }

  void validateResponse(Map<String, dynamic> body) {
    if (!isSingle) return; // Older servers omit layout for legacy sheet responses.
    final manifest = body['output_manifest'];
    final files = body['files'];
    final source = body['source_image_base64'];
    if (body['generation_layout'] != layout || body['generation_mode'] != 'pollinations' ||
        files is! List || files.length != 1 || manifest is! Map ||
        manifest['generation_layout'] != layout || manifest['quantity'] != 1 ||
        source is! String || source.isEmpty) {
      throw StateError('Server did not return one real single-character image');
    }
  }
}

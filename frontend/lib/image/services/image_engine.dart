import '../../character/models/character.dart';
import '../../creative/models/creative_style.dart';
import '../../scene/models/scene.dart';

import '../builders/image_prompt_builder.dart';
import '../models/generated_image.dart';
import '../providers/image_provider.dart';
import '../providers/mock_provider.dart';

class ImageEngine {
  static final ImageProvider _provider =
      MockImageProvider();

  static Future<GeneratedImage> generate({
    required Character character,
    required CreativeStyle creative,
    required Scene scene,
    required Map<String, dynamic> product,
  }) async {
    final prompt = ImagePromptBuilder.build(
      character: character,
      creative: creative,
      scene: scene,
      product: product,
    );

    return _provider.generate(prompt);
  }
}
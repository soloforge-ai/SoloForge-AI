import '../models/generated_image.dart';
import '../models/image_prompt.dart';

abstract class ImageProvider {
  Future<GeneratedImage> generate(
    ImagePrompt prompt,
  );
}
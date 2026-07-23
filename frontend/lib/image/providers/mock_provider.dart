import '../models/generated_image.dart';
import '../models/image_prompt.dart';
import 'image_provider.dart';

class MockImageProvider implements ImageProvider {
  @override
  Future<GeneratedImage> generate(
    ImagePrompt prompt,
  ) async {
   return GeneratedImage(
      provider: 'Mock',
      prompt: prompt.positivePrompt,
      url: '',
    );
  }
}
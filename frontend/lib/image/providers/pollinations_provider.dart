import '../models/generated_image.dart';
import '../models/image_prompt.dart';
import 'image_provider.dart';

/// Pollinations image provider.
///
/// The actual provider request is intentionally routed through the SoloForge
/// backend so secret credentials never live in the Flutter application.
class PollinationsProvider implements ImageProvider {
  final String endpoint;

  const PollinationsProvider({
    required this.endpoint,
  });

  @override
  Future<GeneratedImage> generate(ImagePrompt prompt) async {
    throw UnimplementedError(
      'PollinationsProvider backend transport must be wired to the Render endpoint.',
    );
  }
}

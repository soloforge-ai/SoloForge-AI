import 'prompt_context.dart';
import 'prompt_template.dart';

class VideoPromptService {
  const VideoPromptService();

  String buildProductVideoPrompt(PromptContext context) {
    final template = const PromptTemplate(
      system: 'You are a professional AI video prompt engineer.',

      instruction:
          'Generate a cinematic commercial video prompt for an AI video model.',

      style:
          'Cinematic, realistic, smooth camera movement, premium lighting, 4K quality.',
    );

    final content =
        '''
Subject:
${context.title}

Scene:
Premium product showcase in a clean studio.

Camera:
Slow dolly-in shot followed by a gentle 360-degree orbit.

Motion:
The product slowly rotates while soft particles float in the background.

Lighting:
Soft studio lighting with subtle rim light.

Mood:
${context.mood.isEmpty ? "Premium" : context.mood}

Target Audience:
${context.audience.isEmpty ? "General" : context.audience}

Duration:
8 seconds

Aspect Ratio:
9:16

Output Quality:
4K

Negative Prompt:
Low quality, blurry, watermark, distorted, extra objects, bad anatomy, noisy background.
''';

    return template.build(content: content);
  }
}

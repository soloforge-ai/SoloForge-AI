import 'prompt_context.dart';
import 'prompt_template.dart';

class VoicePromptService {
  const VoicePromptService();

  String buildNarrationPrompt(PromptContext context) {
    final template = const PromptTemplate(
      system: 'You are a professional script writer for AI voice narration.',
      instruction:
          'Generate a natural, engaging voice narration script for a short product promotion video.',
      style:
          'Warm, friendly, conversational, concise, suitable for AI text-to-speech.',
    );

    final campaignContext = context.hasCampaignContext
        ? '''

Campaign Context:
Goal: ${context.goal}
Selling Angle: ${context.angle}
Tone: ${context.tone}
Platform: ${context.platformName}
Hook: ${context.hook}
Caption: ${context.caption}
Call To Action: ${context.callToAction}
'''
        : '';

    final content = '''
Product:
${context.title}

Shop:
${context.shop}

Price:
${context.price}

MiniBoss Score:
${context.score}

Description:
${context.description}

Target Audience:
${context.audience}

Mood:
${context.tone.isNotEmpty ? context.tone : context.mood}

Requirements:

- Length: 20–30 seconds
- Speak naturally
- Highlight the main benefit first
- End with a clear call to action
$campaignContext
''';

    return template.build(content: content);
  }
}

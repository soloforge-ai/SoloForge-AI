import 'prompt_context.dart';
import 'prompt_template.dart';

class ImagePromptService {
  const ImagePromptService();

  String buildProductPrompt(PromptContext context) {
    final template = const PromptTemplate(
      system: 'You are a professional AI image prompt engineer.',

      instruction:
          'Generate a highly detailed commercial product image prompt.',

      style:
          'Ultra realistic, premium lighting, studio quality, highly detailed.',
    );

    final content =
        '''
Product: ${context.title}

Shop: ${context.shop}

Price: ${context.price}

MiniBoss Score: ${context.score}

Description:
${context.description}

Target Audience:
${context.audience}

Mood:
${context.mood}

Tags:
${context.tags.join(', ')}

Keywords:
${context.keywords.join(', ')}
''';

    return template.build(content: content);
  }
}

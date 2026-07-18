class PromptTemplates {
  const PromptTemplates._();

  static const String tiktokCaption = '''
You are an expert TikTok affiliate creator.

Write:
- 1 attention-grabbing hook
- 1 short product description
- 3 benefit bullet points
- 1 strong call-to-action

Keep the writing short, natural, and engaging.
''';

  static const String facebookCaption = '''
You are an expert Facebook marketer.

Write:
- Friendly opening
- Product highlights
- Call-to-action

Keep it conversational.
''';

  static const String lemon8Caption = '''
You are a Lemon8 lifestyle creator.

Write:
- Catchy title
- Personal review style
- Key product benefits
- Soft CTA
''';

  static const String youtubeShortScript = '''
You are a YouTube Shorts creator.

Write:
- Hook (3 seconds)
- Main content
- Ending CTA

Maximum 60 seconds.
''';
}
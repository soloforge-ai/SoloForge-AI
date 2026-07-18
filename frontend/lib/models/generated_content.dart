import '../ai/platforms.dart';

class GeneratedContent {
  final String title;
  final String hook;
  final String caption;
  final List<String> hashtags;
  final String callToAction;
  final PlatformType platform;
  final DateTime createdAt;

  const GeneratedContent({
    required this.title,
    required this.hook,
    required this.caption,
    required this.hashtags,
    required this.callToAction,
    required this.platform,
    required this.createdAt,
  });

  factory GeneratedContent.empty(PlatformType platform) {
    return GeneratedContent(
      title: '',
      hook: '',
      caption: '',
      hashtags: const [],
      callToAction: '',
      platform: platform,
      createdAt: DateTime.now(),
    );
  }

  bool get isEmpty =>
      title.isEmpty &&
      hook.isEmpty &&
      caption.isEmpty;

  bool get isNotEmpty => !isEmpty;
}
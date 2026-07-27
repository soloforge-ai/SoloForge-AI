import 'template_engine.dart';

class TemplateRepository {
  const TemplateRepository();

  final TemplateEngine _engine = const TemplateEngine();

  Future<Map<String, dynamic>> loadTemplate({
    required String platform,
    required String template,
  }) {
    return _engine.loadTemplate(platform: platform, template: template);
  }
}

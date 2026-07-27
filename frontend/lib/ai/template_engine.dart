import 'dart:convert';

import 'package:flutter/services.dart';

class TemplateEngine {
  const TemplateEngine();

  Future<Map<String, dynamic>> loadTemplate({
    required String platform,
    required String template,
  }) async {
    final path = 'assets/templates/$platform/$template.json';

    final jsonString = await rootBundle.loadString(path);

    return jsonDecode(jsonString) as Map<String, dynamic>;
  }
}

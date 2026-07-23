import '../models/creative_style.dart';
import 'creative_loader.dart';

class CreativeEngine {
  static CreativeStyle? _current;

  static Future<void> initialize({
    String id = 'cute',
  }) async {
    _current = await CreativeLoader.loadStyle(id);
  }

  static CreativeStyle get current {
    if (_current == null) {
      throw Exception(
        'CreativeEngine is not initialized.',
      );
    }

    return _current!;
  }
}
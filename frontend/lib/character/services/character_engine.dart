import '../models/character.dart';
import 'character_loader.dart';

class CharacterEngine {
  static Character? _current;

  static Future<void> initialize({
    String id = 'ceo',
  }) async {
    _current = await CharacterLoader.load(id);
  }

  static Character get current {
    if (_current == null) {
      throw Exception(
        'CharacterEngine is not initialized.',
      );
    }

    return _current!;
  }

  static String? reference(String key) {
    return current.reference(key);
  }
}
import '../models/scene.dart';
import 'scene_loader.dart';

class SceneEngine {
  static Scene? _current;

  static Future<void> initialize({
    String id = 'affiliate',
  }) async {
    _current = await SceneLoader.load(id);
  }

  static Scene get current {
    if (_current == null) {
      throw Exception(
        'SceneEngine is not initialized.',
      );
    }

    return _current!;
  }
}
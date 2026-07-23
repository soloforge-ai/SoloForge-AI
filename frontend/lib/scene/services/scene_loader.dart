import 'dart:convert';

import 'package:flutter/services.dart';

import '../models/scene.dart';

class SceneLoader {
  static Future<Scene> load(String id) async {
    final jsonString = await rootBundle.loadString(
      'assets/data/scenes/$id.json',
    );

    return Scene.fromJson(
      jsonDecode(jsonString),
    );
  }
}
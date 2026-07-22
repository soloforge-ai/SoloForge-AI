import 'dart:convert';

import 'package:flutter/services.dart';

import '../models/character.dart';

class CharacterLoader {
  static Future<Character> load(String id) async {
    final jsonString = await rootBundle.loadString(
      'assets/characters/$id/profile.json',
    );

    final Map<String, dynamic> json =
        jsonDecode(jsonString);

    return Character.fromJson(json);
  }
}
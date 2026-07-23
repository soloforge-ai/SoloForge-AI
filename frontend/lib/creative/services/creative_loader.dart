import 'dart:convert';

import 'package:flutter/services.dart';

import '../models/creative_style.dart';

class CreativeLoader {
  static Future<CreativeStyle> loadStyle(String id) async {
    final jsonString = await rootBundle.loadString(
      'assets/data/creative/styles/$id.json',
    );

    return CreativeStyle.fromJson(
      jsonDecode(jsonString),
    );
  }
}
import 'dart:convert';

import 'package:flutter/services.dart';

import '../models/version_info.dart';

class VersionService {
  Future<VersionInfo> loadVersion() async {
    final jsonString =
        await rootBundle.loadString(
      'assets/config/version.json',
    );

    final jsonData =
        json.decode(jsonString);

    return VersionInfo.fromJson({
      ...jsonData,
      'version': const String.fromEnvironment('SOLOFORGE_APP_VERSION', defaultValue: '0.1.2'),
      'build': const int.fromEnvironment('SOLOFORGE_BUILD_NUMBER', defaultValue: 41),
      'channel': 'Alpha',
    });
  }
}
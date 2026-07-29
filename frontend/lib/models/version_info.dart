class VersionInfo {
  final String appName;
  final String company;

  final String version;
  final String channel;
  final int build;

  final String releaseDate;
  final String releaseTime;

  final String engine;
  final String scanner;

  final String apiVersion;

  final String description;

  VersionInfo({
    required this.appName,
    required this.company,
    required this.version,
    required this.channel,
    required this.build,
    required this.releaseDate,
    required this.releaseTime,
    required this.engine,
    required this.scanner,
    required this.apiVersion,
    required this.description,
  });

  factory VersionInfo.fromJson(Map<String, dynamic> json) {
    return VersionInfo(
      appName: json["app_name"],
      company: json["company"],
      version: json["version"],
      channel: json["channel"],
      build: json["build"],
      releaseDate: json["release_date"],
      releaseTime: json["release_time"],
      engine: json["engine"],
      scanner: json["scanner"],
      apiVersion: json["api_version"],
      description: json["description"],
    );
  }

  /// เช่น 0.1.0 Alpha
  String get versionName => "$version $channel";

  /// เช่น 0001
  String get buildNumber => build.toString().padLeft(4, '0');

  /// เช่น 0.1.0-Alpha+0001
  String get fullVersion =>
      "$version-$channel+${build.toString().padLeft(4, '0')}";

  /// เช่น 2026-07-29 15:45 ICT
  String get release =>
      "$releaseDate $releaseTime";

  @override
  String toString() {
    return '''
$appName

Version : $versionName
Build : $buildNumber
Release : $release

Engine : $engine
Scanner : $scanner
API : $apiVersion
''';
  }
}
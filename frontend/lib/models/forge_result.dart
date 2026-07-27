class ForgeResult {
  final String hook;

  final String caption;

  final String cta;

  final String script;

  const ForgeResult({
    required this.hook,
    required this.caption,
    required this.cta,
    required this.script,
  });

  factory ForgeResult.empty() {
    return const ForgeResult(hook: '', caption: '', cta: '', script: '');
  }

  Map<String, dynamic> toJson() {
    return {'hook': hook, 'caption': caption, 'cta': cta, 'script': script};
  }

  factory ForgeResult.fromJson(Map<String, dynamic> json) {
    return ForgeResult(
      hook: json['hook'] ?? '',
      caption: json['caption'] ?? '',
      cta: json['cta'] ?? '',
      script: json['script'] ?? '',
    );
  }

  ForgeResult copyWith({
    String? hook,
    String? caption,
    String? cta,
    String? script,
  }) {
    return ForgeResult(
      hook: hook ?? this.hook,
      caption: caption ?? this.caption,
      cta: cta ?? this.cta,
      script: script ?? this.script,
    );
  }
}

class AffiliateContentClaim {
  const AffiliateContentClaim({
    required this.claimText,
    required this.claimType,
    required this.evidenceRequired,
    required this.verificationStatus,
  });

  final String claimText;
  final String claimType;
  final String evidenceRequired;
  final String verificationStatus;

  factory AffiliateContentClaim.fromJson(Map<String, dynamic> json) {
    return AffiliateContentClaim(
      claimText: json['claim_text']?.toString() ?? '',
      claimType: json['claim_type']?.toString() ?? 'product_claim',
      evidenceRequired: json['evidence_required']?.toString() ?? '',
      verificationStatus:
          json['verification_status']?.toString() ?? 'unverified',
    );
  }
}

class AffiliateContentTool {
  const AffiliateContentTool({
    required this.toolName,
    required this.role,
    required this.usedInFinalOutput,
  });

  final String toolName;
  final String role;
  final bool usedInFinalOutput;

  factory AffiliateContentTool.fromJson(Map<String, dynamic> json) {
    return AffiliateContentTool(
      toolName: json['tool_name']?.toString() ?? '',
      role: json['role']?.toString() ?? '',
      usedInFinalOutput: json['used_in_final_output'] == true,
    );
  }
}

class AffiliateEndCardItem {
  const AffiliateEndCardItem({
    required this.role,
    required this.tool,
  });

  final String role;
  final String tool;

  factory AffiliateEndCardItem.fromJson(Map<String, dynamic> json) {
    return AffiliateEndCardItem(
      role: json['role']?.toString() ?? '',
      tool: json['tool']?.toString() ?? '',
    );
  }
}

class AffiliateContentPackage {
  const AffiliateContentPackage({
    required this.programSlug,
    required this.programName,
    required this.platform,
    required this.format,
    required this.intent,
    required this.goal,
    required this.title,
    required this.hooks,
    required this.script,
    required this.shotList,
    required this.voiceover,
    required this.visualPrompts,
    required this.thumbnailBrief,
    required this.cta,
    required this.description,
    required this.affiliateDisclosure,
    required this.claims,
    required this.tools,
    required this.endCardHeading,
    required this.endCardItems,
    required this.endCardClosing,
    this.affiliateUrl,
  });

  final String programSlug;
  final String programName;
  final String platform;
  final String format;
  final String intent;
  final String goal;
  final String title;
  final List<String> hooks;
  final String script;
  final List<String> shotList;
  final String voiceover;
  final List<String> visualPrompts;
  final String thumbnailBrief;
  final String cta;
  final String description;
  final String affiliateDisclosure;
  final String? affiliateUrl;
  final List<AffiliateContentClaim> claims;
  final List<AffiliateContentTool> tools;
  final String endCardHeading;
  final List<AffiliateEndCardItem> endCardItems;
  final String endCardClosing;

  bool get hasUnverifiedClaims =>
      claims.any((claim) => claim.verificationStatus == 'unverified');

  factory AffiliateContentPackage.fromJson(Map<String, dynamic> json) {
    final endCard = _map(json['end_card']);
    return AffiliateContentPackage(
      programSlug: json['program_slug']?.toString() ?? '',
      programName: json['program_name']?.toString() ?? '',
      platform: json['platform']?.toString() ?? '',
      format: json['format']?.toString() ?? '',
      intent: json['intent']?.toString() ?? '',
      goal: json['goal']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      hooks: _strings(json['hooks']),
      script: json['script']?.toString() ?? '',
      shotList: _strings(json['shot_list']),
      voiceover: json['voiceover']?.toString() ?? '',
      visualPrompts: _strings(json['visual_prompts']),
      thumbnailBrief: json['thumbnail_brief']?.toString() ?? '',
      cta: json['cta']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      affiliateDisclosure: json['affiliate_disclosure']?.toString() ?? '',
      affiliateUrl: _nullableString(json['affiliate_url']),
      claims: _maps(json['claims'])
          .map(AffiliateContentClaim.fromJson)
          .toList(growable: false),
      tools: _maps(json['tools'])
          .map(AffiliateContentTool.fromJson)
          .toList(growable: false),
      endCardHeading: endCard['heading']?.toString() ?? 'เบื้องหลังคลิปนี้',
      endCardItems: _maps(endCard['items'])
          .map(AffiliateEndCardItem.fromJson)
          .toList(growable: false),
      endCardClosing:
          endCard['closing']?.toString() ?? 'ทดลองจริง ใช้จริง แล้วค่อยเล่า',
    );
  }

  String toCopyableText() {
    final buffer = StringBuffer()
      ..writeln(title)
      ..writeln()
      ..writeln('HOOKS')
      ..writeln(hooks.map((item) => '• $item').join('\n'))
      ..writeln()
      ..writeln('SCRIPT')
      ..writeln(script)
      ..writeln()
      ..writeln('SHOT LIST')
      ..writeln(shotList.map((item) => '• $item').join('\n'))
      ..writeln()
      ..writeln('VOICEOVER')
      ..writeln(voiceover)
      ..writeln()
      ..writeln('CTA')
      ..writeln(cta)
      ..writeln()
      ..writeln('DESCRIPTION')
      ..writeln(description)
      ..writeln()
      ..writeln('AFFILIATE DISCLOSURE')
      ..writeln(affiliateDisclosure);
    if (affiliateUrl != null) {
      buffer
        ..writeln()
        ..writeln('AFFILIATE URL')
        ..writeln(affiliateUrl);
    }
    return buffer.toString().trim();
  }

  static Map<String, dynamic> _map(Object? value) {
    if (value is Map<String, dynamic>) return value;
    if (value is Map) {
      return value.map((key, value) => MapEntry(key.toString(), value));
    }
    return const {};
  }

  static List<Map<String, dynamic>> _maps(Object? value) {
    if (value is! List) return const [];
    return value.whereType<Map>().map((item) {
      return item.map((key, value) => MapEntry(key.toString(), value));
    }).toList(growable: false);
  }

  static List<String> _strings(Object? value) {
    if (value is! List) return const [];
    return value
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }

  static String? _nullableString(Object? value) {
    final text = value?.toString().trim();
    return text == null || text.isEmpty ? null : text;
  }
}

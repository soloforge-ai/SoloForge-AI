class AffiliateProgram {
  const AffiliateProgram({
    required this.slug,
    required this.name,
    required this.source,
    this.website,
    this.category,
    this.shortDescription,
    this.description,
    this.commissionType,
    this.commissionRate,
    this.commissionValue,
    this.cookieDays,
    this.verified = false,
    this.signupUrl,
    this.restrictions,
    this.freeTrial,
    this.tags = const [],
    this.agentKeywords = const [],
    this.agentUseCases = const [],
  });

  final String slug;
  final String name;
  final String source;
  final String? website;
  final String? category;
  final String? shortDescription;
  final String? description;
  final String? commissionType;
  final String? commissionRate;
  final double? commissionValue;
  final int? cookieDays;
  final bool verified;
  final String? signupUrl;
  final String? restrictions;
  final bool? freeTrial;
  final List<String> tags;
  final List<String> agentKeywords;
  final List<String> agentUseCases;

  factory AffiliateProgram.fromJson(Map<String, dynamic> json) {
    final commission = _map(json['commission']);
    final agents = _map(json['agents']);

    return AffiliateProgram(
      slug: json['slug']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      source: json['source']?.toString() ?? 'unknown',
      website: _nullableString(json['website']),
      category: _nullableString(json['category']),
      shortDescription: _nullableString(json['short_description']),
      description: _nullableString(json['description']),
      commissionType: _nullableString(commission['type']),
      commissionRate: _nullableString(commission['rate']),
      commissionValue: _nullableDouble(commission['value']),
      cookieDays: _nullableInt(json['cookie_days']),
      verified: json['verified'] == true,
      signupUrl: _nullableString(json['signup_url']),
      restrictions: _nullableString(json['restrictions']),
      freeTrial: json['free_trial'] is bool ? json['free_trial'] as bool : null,
      tags: _strings(json['tags']),
      agentKeywords: _strings(agents['keywords']),
      agentUseCases: _strings(agents['use_cases']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'slug': slug,
      'name': name,
      'source': source,
      'website': website,
      'category': category,
      'short_description': shortDescription,
      'description': description,
      'commission': {
        'type': commissionType,
        'rate': commissionRate,
        'value': commissionValue,
      },
      'cookie_days': cookieDays,
      'verified': verified,
      'signup_url': signupUrl,
      'restrictions': restrictions,
      'free_trial': freeTrial,
      'tags': tags,
      'agents': {
        'keywords': agentKeywords,
        'use_cases': agentUseCases,
      },
    };
  }

  String get commissionLabel {
    final recurring = (commissionType ?? '').toLowerCase().contains('recurr')
        ? ' recurring'
        : '';
    if (commissionRate != null && commissionRate!.isNotEmpty) {
      return '${commissionRate!}$recurring';
    }
    if (commissionValue != null) {
      final digits = commissionValue! % 1 == 0 ? 0 : 1;
      return '${commissionValue!.toStringAsFixed(digits)}$recurring';
    }
    return commissionType?.isNotEmpty == true ? commissionType! : 'Not published';
  }

  static Map<String, dynamic> _map(Object? value) {
    return value is Map<String, dynamic> ? value : const {};
  }

  static List<String> _strings(Object? value) {
    if (value is! List) return const [];
    return value.map((item) => item.toString()).toList(growable: false);
  }

  static String? _nullableString(Object? value) {
    final text = value?.toString().trim();
    return text == null || text.isEmpty ? null : text;
  }

  static double? _nullableDouble(Object? value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '');
  }

  static int? _nullableInt(Object? value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '');
  }
}

class AffiliateOpportunityScore {
  const AffiliateOpportunityScore({
    required this.audienceFit,
    required this.contentPotential,
    required this.commissionScore,
    required this.productValue,
    required this.competition,
    required this.totalScore,
    required this.rationale,
    required this.risks,
    required this.contentAngles,
  });

  final double audienceFit;
  final double contentPotential;
  final double commissionScore;
  final double productValue;
  final double competition;
  final double totalScore;
  final List<String> rationale;
  final List<String> risks;
  final List<String> contentAngles;

  factory AffiliateOpportunityScore.fromJson(Map<String, dynamic> json) {
    return AffiliateOpportunityScore(
      audienceFit: _score(json['audience_fit']),
      contentPotential: _score(json['content_potential']),
      commissionScore: _score(json['commission_score']),
      productValue: _score(json['product_value']),
      competition: _score(json['competition']),
      totalScore: _score(json['total_score']),
      rationale: _strings(json['rationale']),
      risks: _strings(json['risks']),
      contentAngles: _strings(json['content_angles']),
    );
  }

  static double _score(Object? value) =>
      value is num ? value.toDouble() : double.tryParse('$value') ?? 0;

  static List<String> _strings(Object? value) {
    if (value is! List) return const [];
    return value.map((item) => item.toString()).toList(growable: false);
  }
}

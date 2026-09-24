import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/affiliate_program.dart';

void main() {
  test('AffiliateProgram parses normalized backend payload', () {
    final program = AffiliateProgram.fromJson({
      'slug': 'tool-a',
      'name': 'Tool A',
      'source': 'openaffiliate',
      'category': 'AI',
      'commission': {
        'type': 'recurring',
        'rate': '30%',
        'value': 30,
      },
      'cookie_days': 60,
      'verified': true,
      'agents': {
        'keywords': ['ai-video', 'creator'],
        'use_cases': ['YouTube production'],
      },
    });

    expect(program.slug, 'tool-a');
    expect(program.commissionLabel, '30% recurring');
    expect(program.cookieDays, 60);
    expect(program.verified, isTrue);
    expect(program.agentKeywords, contains('creator'));
  });

  test('AffiliateOpportunityScore parses deterministic score response', () {
    final score = AffiliateOpportunityScore.fromJson({
      'audience_fit': 80,
      'content_potential': 75,
      'commission_score': 90,
      'product_value': 70,
      'competition': 50,
      'total_score': 77.25,
      'rationale': ['Recurring commission.'],
      'risks': ['Verify terms.'],
      'content_angles': ['Hands-on review'],
    });

    expect(score.totalScore, 77.25);
    expect(score.rationale, isNotEmpty);
    expect(score.contentAngles.single, 'Hands-on review');
  });
}

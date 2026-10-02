import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/content_job.dart';
import 'package:frontend/pages/content_job_page.dart';

ContentJob jobWithQuality(dynamic semanticFidelity) {
  return ContentJob(
    id: '11111111-1111-1111-1111-111111111111',
    idea: 'Telegram Bot automation',
    status: 'READY_FOR_REVIEW',
    publishPlatform: 'facebook',
    publishStatus: 'PENDING',
    hook: 'Telegram Bot ทำอะไรได้มากกว่าตอบแชท?',
    caption: 'ตัวอย่างการต่อ Telegram Bot ให้กลายเป็น automation workflow',
    generatorProvider: 'gemini',
    generatorModel: 'gemini-3.5-flash-lite',
    contentPackage: {
      'format': 'question_post',
      if (semanticFidelity != null) 'semantic_fidelity': semanticFidelity,
    },
  );
}

void main() {
  test('semantic PASS is available and does not block approval', () {
    final review = ContentQualityReview.fromJob(
      jobWithQuality({
        'status': 'PASS',
        'reason': 'Generated body preserves subject anchors.',
        'required_anchors': ['telegram', 'bot'],
        'matched_anchors': ['telegram', 'bot'],
      }),
    );

    expect(review.available, isTrue);
    expect(review.status, 'PASS');
    expect(review.blocksApproval, isFalse);
    expect(review.requiredAnchors, ['telegram', 'bot']);
    expect(review.matchedAnchors, ['telegram', 'bot']);
  });

  test('semantic FAIL blocks approval', () {
    final review = ContentQualityReview.fromJob(
      jobWithQuality({
        'status': 'FAIL',
        'reason': 'Generated body lost the identifiable subject.',
        'required_anchors': ['telegram'],
        'matched_anchors': <String>[],
      }),
    );

    expect(review.available, isTrue);
    expect(review.status, 'FAIL');
    expect(review.blocksApproval, isTrue);
  });

  test('legacy job without semantic metadata stays reviewable', () {
    final review = ContentQualityReview.fromJob(jobWithQuality(null));

    expect(review.available, isFalse);
    expect(review.status, 'NOT_AVAILABLE');
    expect(review.blocksApproval, isFalse);
    expect(
      review.reason,
      'Semantic fidelity metadata is not available for this job.',
    );
  });

  test('malformed anchor metadata is handled safely', () {
    final review = ContentQualityReview.fromJob(
      jobWithQuality({
        'status': 'PASS',
        'reason': '',
        'required_anchors': 'telegram',
        'matched_anchors': null,
      }),
    );

    expect(review.available, isTrue);
    expect(review.requiredAnchors, isEmpty);
    expect(review.matchedAnchors, isEmpty);
    expect(review.blocksApproval, isFalse);
  });
}

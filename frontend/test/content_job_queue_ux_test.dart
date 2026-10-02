import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/content_job.dart';
import 'package:frontend/pages/home_page.dart';

ContentJob job(String status, {String publishStatus = 'PENDING'}) {
  return ContentJob(
    id: '9fa31f8e-3a34-405a-9aaa-4e487e68fd32',
    idea: 'Telegram Bot automation',
    status: status,
    publishPlatform: 'facebook',
    publishStatus: publishStatus,
    contentPackage: const {
      'format': 'question_post',
    },
  );
}

void main() {
  test('action-required states are grouped ahead of other work', () {
    final review = job('READY_FOR_REVIEW');
    final publish = job('READY_TO_PUBLISH');
    final failed = job('GENERATION_FAILED');

    expect(
      JobQueuePresentation.groupFor(review),
      QueueFilter.actionRequired,
    );
    expect(
      JobQueuePresentation.groupFor(publish),
      QueueFilter.actionRequired,
    );
    expect(
      JobQueuePresentation.groupFor(failed),
      QueueFilter.actionRequired,
    );
    expect(JobQueuePresentation.statusRank(review), 0);
    expect(JobQueuePresentation.statusRank(publish), 0);
    expect(JobQueuePresentation.statusRank(failed), 1);
  });

  test('processing completed and backlog states remain distinguishable', () {
    expect(
      JobQueuePresentation.groupFor(job('GENERATING')),
      QueueFilter.processing,
    );
    expect(
      JobQueuePresentation.groupFor(job('PUBLISHED')),
      QueueFilter.completed,
    );
    expect(
      JobQueuePresentation.groupFor(job('BACKLOG')),
      QueueFilter.backlog,
    );
  });

  test('queue exposes human-readable statuses and next actions', () {
    expect(
      JobQueuePresentation.statusLabel('READY_TO_PUBLISH'),
      'Ready to Publish',
    );
    expect(
      JobQueuePresentation.actionLabel(job('READY_FOR_REVIEW')),
      'Review now',
    );
    expect(
      JobQueuePresentation.actionLabel(job('READY_TO_PUBLISH')),
      'Publish now',
    );
    expect(
      JobQueuePresentation.actionLabel(job('PUBLISH_FAILED')),
      'Needs attention',
    );
    expect(
      JobQueuePresentation.actionLabel(job('PUBLISHED')),
      'Completed',
    );
  });
}

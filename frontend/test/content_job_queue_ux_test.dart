import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/content_job.dart';
import 'package:frontend/pages/home_page.dart';

ContentJob job(
  String status, {
  String publishStatus = 'PENDING',
  bool needsVideo = false,
}) {
  return ContentJob(
    id: '9fa31f8e-3a34-405a-9aaa-4e487e68fd32',
    idea: 'Telegram Bot automation',
    status: status,
    publishPlatform: 'facebook',
    publishStatus: publishStatus,
    contentPackage: {
      'format': 'question_post',
      'needs_video': needsVideo,
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

  test('passive video backlog is not misclassified as action required', () {
    final videoBacklog = job('BACKLOG', needsVideo: true);

    expect(videoBacklog.blocker, 'Waiting for video pipeline');
    expect(JobQueuePresentation.isFailure(videoBacklog), isFalse);
    expect(
      JobQueuePresentation.groupFor(videoBacklog),
      QueueFilter.backlog,
    );
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


  test('search matches multiple terms across human-readable job metadata', () {
    final review = job('READY_FOR_REVIEW');

    expect(
      JobQueuePresentation.matchesSearch(review, 'telegram review'),
      isTrue,
    );
    expect(
      JobQueuePresentation.matchesSearch(review, 'facebook question'),
      isTrue,
    );
    expect(
      JobQueuePresentation.matchesSearch(review, 'ready review'),
      isTrue,
    );
    expect(
      JobQueuePresentation.matchesSearch(review, 'publish now'),
      isFalse,
    );
  });

  test('search is case-insensitive and supports short job id', () {
    final review = job('READY_FOR_REVIEW');

    expect(
      JobQueuePresentation.matchesSearch(review, '9FA31F8E'),
      isTrue,
    );
    expect(
      JobQueuePresentation.matchesSearch(review, 'TELEGRAM FACEBOOK'),
      isTrue,
    );
  });

  test('empty search matches every job', () {
    expect(
      JobQueuePresentation.matchesSearch(job('BACKLOG'), '   '),
      isTrue,
    );
  });

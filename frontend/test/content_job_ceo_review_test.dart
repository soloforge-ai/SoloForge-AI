import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/content_job.dart';
import 'package:frontend/pages/content_job_page.dart';
import 'package:frontend/services/content_job_service.dart';
import 'package:frontend/services/soloforge_session_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

final png = base64Decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=');
const signedUrl = 'https://storage.example.com/storage/v1/object/sign/content-assets/job/image.png?token=offline';
ContentAssetPreview imagePreview({String? digest}) => ContentAssetPreview(
  url: signedUrl, mediaType: 'image', assetStatus: 'READY', pipelineRoute: 'VIDEO',
  assetSha256: digest ?? sha256.convert(png).toString(),
);
ContentJob reviewJob({bool ceo = true, String status = 'READY_FOR_REVIEW'}) => ContentJob.fromJson({
  'id': 'job', 'idea': 'Offline review', 'status': status,
  'content_package': {
    if (ceo) 'ceo_identity_required': true,
    if (ceo) 'asset_status': 'READY',
    if (ceo) 'asset_storage_path': 'job/image.png',
    'pipeline_route': ceo ? 'VIDEO' : 'TEXT',
  },
});

class OfflineSession extends SoloForgeSessionService {
  @override
  Future<Map<String, String>> authorizationHeaders() async => {'Authorization': 'Bearer offline-owner'};
}

class ReviewService extends ContentJobService {
  final image = Completer<Uint8List>();
  final decisions = <bool>[];
  int ordinaryApprovals = 0;
  @override
  Future<ContentAssetPreview> getAssetPreview(String id) async => imagePreview();
  @override
  Future<Uint8List> downloadReviewImage(ContentAssetPreview preview) => image.future;
  @override
  Future<ContentFeedback> getPerformanceFeedback(String id) async => throw Exception('Offline');
  @override
  Future<ContentJob> reviewAsset(String id, {
    required ContentAssetPreview preview, required Uint8List displayedImage, required bool approved,
  }) async {
    expect(displayedImage, same(png));
    expect(sha256.convert(displayedImage).toString(), preview.assetSha256);
    decisions.add(approved);
    return reviewJob(status: approved ? 'ASSET_READY' : 'READY_FOR_REVIEW');
  }
  @override
  Future<ContentJob> approve(String id) async {
    ordinaryApprovals++;
    return reviewJob(ceo: false, status: 'APPROVED');
  }
}

void main() {
  for (final approved in [true, false]) {
    test('explicit ${approved ? 'approval' : 'rejection'} sends displayed image digest and owner auth', () async {
      var posts = 0;
      final service = ContentJobService(
        sessionService: OfflineSession(), storageOrigin: 'https://storage.example.com',
        client: MockClient((request) async {
          if (request.method == 'GET') {
            expect(request.url.toString(), signedUrl);
            expect(request.headers.containsKey('Authorization'), isFalse);
            return http.Response.bytes(png, 200, headers: {'content-type': 'image/png'});
          }
          expect(request.url.path, '/v1/content-jobs/job/asset-review');
          expect(request.headers['Authorization'], 'Bearer offline-owner');
          expect(jsonDecode(request.body), {
            'decision': approved ? 'APPROVED' : 'REJECTED',
            'asset_sha256': sha256.convert(png).toString(),
          });
          posts++;
          return http.Response('{"id":"job","status":"READY_FOR_REVIEW"}', 200);
        }),
      );
      final preview = imagePreview();
      final displayed = await service.downloadReviewImage(preview);
      await service.reviewAsset('job', preview: preview, displayedImage: displayed, approved: approved);
      expect(posts, 1);
    });
  }

  test('stale or missing hashes stop before review POST', () async {
    var posts = 0;
    final service = ContentJobService(
      sessionService: OfflineSession(), storageOrigin: 'https://storage.example.com',
      client: MockClient((request) async {
        if (request.method != 'GET') posts++;
        return http.Response.bytes(png, 200, headers: {'content-type': 'image/png'});
      }),
    );
    final stale = imagePreview(digest: '0' * 64);
    await expectLater(service.downloadReviewImage(stale), throwsFormatException);
    await expectLater(service.reviewAsset('job', preview: stale, displayedImage: png, approved: true), throwsFormatException);
    const missing = ContentAssetPreview(url: signedUrl, mediaType: 'image', assetStatus: 'READY', pipelineRoute: 'VIDEO');
    await expectLater(service.reviewAsset('job', preview: missing, displayedImage: png, approved: false), throwsFormatException);
    expect(posts, 0);
  });

  for (final approved in [true, false]) {
    testWidgets('CEO ${approved ? 'approve' : 'reject'} requires displayed memory image and never ordinary approve', (tester) async {
      final service = ReviewService();
      await tester.pumpWidget(MaterialApp(home: ContentJobPage(job: reviewJob(), service: service)));
      await tester.pump();
      await tester.scrollUntilVisible(find.text('Approve CEO image'), 400,
          scrollable: find.byType(Scrollable).first);
      final approveButton = find.ancestor(
        of: find.text('Approve CEO image'),
        matching: find.byWidgetPredicate((widget) => widget is FilledButton),
      );
      expect(tester.widget<FilledButton>(approveButton).onPressed, isNull);
      service.image.complete(png);
      await tester.pump();
      await tester.scrollUntilVisible(find.byType(Image), -400,
          scrollable: find.byType(Scrollable).first);
      await tester.runAsync(() => precacheImage(
          MemoryImage(png), tester.element(find.byType(Image))));
      await tester.pumpAndSettle();
      expect((tester.widget<Image>(find.byType(Image)).image as MemoryImage).bytes, same(png));
      final action = find.text(approved ? 'Approve CEO image' : 'Reject CEO image');
      await tester.scrollUntilVisible(action, 400,
          scrollable: find.byType(Scrollable).first);
      await tester.tap(action);
      await tester.pumpAndSettle();
      expect(service.decisions, [approved]);
      expect(service.ordinaryApprovals, 0);
    });
  }

  testWidgets('ordinary content still uses ordinary approve', (tester) async {
    final service = ReviewService();
    await tester.pumpWidget(MaterialApp(home: ContentJobPage(job: reviewJob(ceo: false), service: service)));
    await tester.pumpAndSettle();
    final action = find.text('Approve');
    await tester.scrollUntilVisible(action, 400,
        scrollable: find.byType(Scrollable).first);
    await tester.tap(action);
    await tester.pumpAndSettle();
    expect(service.ordinaryApprovals, 1);
    expect(service.decisions, isEmpty);
  });
}

import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:frontend/models/content_job.dart';
import 'package:frontend/pages/content_job_page.dart';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/content_job_service.dart';
import 'package:frontend/services/soloforge_session_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('resolveProduct uses authenticated endpoint and returns grounded job', () async {
    var bootstrapCalls = 0;
    var resolverCalls = 0;
    final client = MockClient((request) async {
      if (request.url.path == '/auth/soloforge/bootstrap') {
        bootstrapCalls++;
        expect(request.method, 'POST');
        expect(request.headers['Authorization'], 'Bearer supabase-token');
        return http.Response(
          jsonEncode({'session_token': 'owner-app-token'}),
          200,
          headers: {'content-type': 'application/json'},
        );
      }

      if (request.url.path ==
          '/v1/content-jobs/job-1/resolve-product') {
        resolverCalls++;
        expect(request.method, 'POST');
        expect(request.headers['Authorization'], 'Bearer owner-app-token');
        expect(request.headers['Content-Type'], contains('application/json'));
        expect(
          jsonDecode(request.body),
          {'url': 'https://s.shopee.co.th/example'},
        );
        return http.Response(
          jsonEncode({
            'id': 'job-1',
            'idea': 'Product post',
            'status': 'READY_FOR_REVIEW',
            'publish_platform': 'facebook',
            'publish_status': 'PENDING',
            'qa_status': 'PENDING',
            'content_package': {
              'goal': 'conversion',
              'product_grounding_status': 'READY',
              'product_grounding': {
                'canonical_title': 'Example Product',
                'image_urls': ['https://cdn.example/product.jpg'],
              },
              'product_resolution': {
                'provider': 'shopee',
                'resolved_url': 'https://shopee.co.th/product/1/2',
              },
            },
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }

      throw StateError('Unexpected request: ${request.method} ${request.url}');
    });

    final session = SoloForgeSessionService(
      client: client,
      currentIdentity: () => (
        userId: 'owner',
        accessToken: 'supabase-token',
      ),
    );
    final service = ContentJobService(
      client: client,
      sessionService: session,
    );

    final job = await service.resolveProduct(
      'job-1',
      url: 'https://s.shopee.co.th/example',
    );

    expect(bootstrapCalls, 1);
    expect(resolverCalls, 1);
    expect(job.status, 'READY_FOR_REVIEW');
    expect(job.qaStatus, 'PENDING');
    expect(job.contentPackage['product_grounding_status'], 'READY');
    expect(
      (job.contentPackage['product_resolution'] as Map)['provider'],
      'shopee',
    );

    session.dispose();
  });
  testWidgets('HTTP 400 stays beside resolver button without retry or URL loss',
      (tester) async {
    tester.view.physicalSize = const Size(1000, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    var resolverCalls = 0;
    final pending = Completer<http.Response>();
    final client = MockClient((request) async {
      if (request.url.path == '/auth/soloforge/bootstrap') {
        return http.Response(jsonEncode({'session_token': 'test-app-token'}), 200);
      }
      if (request.url.path.endsWith('/resolve-product')) {
        resolverCalls++;
        expect(jsonDecode(request.body),
            {'url': 'https://s.shopee.co.th/entered-url'});
        return pending.future;
      }
      return http.Response('{}', 404); // Advisory feedback only.
    });
    final session = SoloForgeSessionService(
      client: client,
      currentIdentity: () => (userId: 'owner', accessToken: 'test-token'),
    );
    addTearDown(session.dispose);
    final service = ContentJobService(client: client, sessionService: session);
    const job = ContentJob(
      id: 'job-1', idea: 'Product post', status: 'READY_FOR_REVIEW',
      publishPlatform: 'facebook', publishStatus: 'PENDING',
      contentPackage: {'goal': 'conversion'},
    );
    await tester.pumpWidget(MaterialApp(
      home: ContentJobPage(job: job, service: service),
    ));
    await tester.pumpAndSettle();
    final input = find.widgetWithText(TextField, 'Shopee product URL');
    await tester.ensureVisible(input);
    await tester.enterText(input, 'https://s.shopee.co.th/entered-url');
    final button = find.widgetWithText(FilledButton, 'Resolve Product');
    await tester.ensureVisible(button);
    await tester.tap(button);
    await tester.pump();
    expect(resolverCalls, 1);
    expect(tester.widget<FilledButton>(button).onPressed, isNull);
    pending.complete(http.Response(jsonEncode({
      'detail': 'Shopee product title could not be resolved',
    }), 400));
    await tester.pumpAndSettle();
    final error = find.byKey(const ValueKey('product-resolver-error'));
    expect(error, findsOneWidget);
    expect(find.text('Shopee product title could not be resolved'), findsOneWidget);
    final gap = tester.getTopLeft(error).dy - tester.getBottomLeft(button).dy;
    expect(gap, inInclusiveRange(0, 16));
    expect(tester.widget<TextField>(input).controller!.text,
        'https://s.shopee.co.th/entered-url');
    expect(tester.widget<FilledButton>(button).onPressed, isNotNull);
    await tester.pump(const Duration(seconds: 31));
    expect(resolverCalls, 1);
  });
}

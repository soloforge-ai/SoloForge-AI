import 'dart:convert';

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
}

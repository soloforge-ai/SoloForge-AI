import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/pages/byop_page.dart';
import 'package:frontend/services/byop_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets('Cloudflare model, private preview and existing review use mock API only', (tester) async {
    final bytes = base64Decode('iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAADElEQVR4nGNgGB4AAADIAAGtQHYiAAAAAElFTkSuQmCC');
    final hash = sha256.convert(bytes).toString();
    var status = 'READY_FOR_REVIEW';
    var reviews = 0;
    final service = ByopService(member: false,
      applicationAuthorization: () async => {'Authorization': 'Bearer offline-owner'},
      client: MockClient((request) async {
        expect(request.url.queryParameters['provider'], 'cloudflare');
        expect(request.headers['Authorization'], 'Bearer offline-owner');
        final path = request.url.path;
        if (path.endsWith('/session')) {
          return http.Response(jsonEncode({'principal':'owner:fixture', 'cloudflare_offline_available':true,
            'readiness':{'pilot_role_eligible':true, 'offline_mock_enabled':true, 'generation_enabled':false}}), 200);
        }
        if (path.endsWith('/credentials')) return http.Response('{"credentials":[]}', 200);
        if (path.endsWith('/asset-review')) {
          final body = jsonDecode(request.body) as Map;
          expect(body['asset_sha256'], hash);
          expect(body['decision'], 'APPROVED');
          reviews++; status = 'ASSET_READY';
          return http.Response('{}', 200);
        }
        if (path.endsWith('/asset')) return http.Response.bytes(bytes, 200);
        if (path.endsWith('/jobs')) {
          final body = jsonDecode(request.body) as Map;
          expect((body['asset_forge_request'] as Map)['model'], '@cf/black-forest-labs/flux-1-schnell');
          return http.Response('{"id":"offline-job"}', 200);
        }
        if (path.endsWith('/jobs/offline-job')) {
          return http.Response(jsonEncode({
            'id':'offline-job', 'status':status, 'content_package':{'asset_sha256':hash}}), 200);
        }
        fail('Unexpected request: ${request.method} $path');
      }));
    service.provider = 'cloudflare';
    await tester.pumpWidget(MaterialApp(home: ByopPage(member: false, service: service)));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('FLUX.1 Schnell'), 300,
      scrollable: find.byType(Scrollable).first);
    expect(find.text('FLUX.1 Schnell'), findsOneWidget);
    final create = find.text('Create mock image job');
    await tester.scrollUntilVisible(create, 300, scrollable: find.byType(Scrollable).first);
    await tester.tap(create); await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.byType(Image), 300, scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    expect(find.byType(Image), findsOneWidget);
    final approve = find.text('Approve displayed image');
    await tester.scrollUntilVisible(approve, 300, scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    await tester.tap(approve); await tester.pumpAndSettle();
    expect(reviews, 1);
    await tester.scrollUntilVisible(find.textContaining('Status: ASSET_READY'), -300,
      scrollable: find.byType(Scrollable).first);
    expect(find.textContaining('Status: ASSET_READY'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Render approved image'), 300,
      scrollable: find.byType(Scrollable).first);
    final render = tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Render approved image'));
    expect(render.onPressed, isNull);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('disabled Cloudflare surfaces error and offers no execution controls', (tester) async {
    var mutations = 0;
    final service = ByopService(member: false,
      applicationAuthorization: () async => {'Authorization':'Bearer offline-owner'},
      client: MockClient((request) async {
        if (request.method != 'GET') mutations++;
        return http.Response('{"detail":"Cloudflare offline capability is disabled"}', 503);
      }));
    service.provider = 'cloudflare';
    await tester.pumpWidget(MaterialApp(home: ByopPage(member: false, service: service)));
    await tester.pumpAndSettle();
    expect(find.textContaining('Cloudflare offline capability is disabled'), findsOneWidget);
    expect(find.text('Generate mock image once'), findsNothing);
    expect(mutations, 0);
    await tester.pumpWidget(const SizedBox());
  });
}

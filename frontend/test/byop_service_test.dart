// Mock-only tests intended for CI; Flutter SDK unavailable in local executor.
import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/byop_service.dart';
import 'package:frontend/services/pollinations_session_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  test('server readiness stays distinct from authenticated member access', () async {
    final client = ByopService(member: true,
      applicationAuthorization: () async => {'Authorization': 'Bearer member-fixture'},
      client: MockClient((request) async => http.Response(jsonEncode({
        'principal': 'member:fixture',
        'readiness': {'pilot_role_eligible': false, 'generation_enabled': false,
          'earnings': {'confirmed': false}, 'total_cost_micro_pollen': null},
      }), 200)));
    await client.headers();
    expect(client.readiness['pilot_role_eligible'], isFalse);
    expect(client.readiness['generation_enabled'], isFalse);
    expect(client.readiness['total_cost_micro_pollen'], isNull);
    expect((client.readiness['earnings'] as Map)['confirmed'], isFalse);
    client.dispose();
  });

  test('member request uses Supabase bearer and active principal, without owner bootstrap', () async {
    final calls = <String>[];
    final client = ByopService(member: true,
      applicationAuthorization: () async => {'Authorization': 'Bearer member-fixture'},
      client: MockClient((request) async {
        calls.add(request.url.path);
        expect(request.headers['Authorization'], 'Bearer member-fixture');
        if (request.url.path.endsWith('/session')) {
          return http.Response(jsonEncode({'principal': 'member:fixture'}), 200);
        }
        return http.Response('{"id":"job-fixture"}', 200);
      }));
    expect((await client.post('jobs', {'asset_forge_request': {}}))['id'], 'job-fixture');
    expect(calls, ['/v1/byop/session', '/v1/byop/jobs']);
    client.dispose();
  });

  test('inactive membership denies mutation before request', () async {
    var mutations = 0;
    final client = ByopService(member: true,
      applicationAuthorization: () async => {'Authorization': 'Bearer inactive-fixture'},
      client: MockClient((request) async {
        if (request.method == 'POST') mutations++;
        return http.Response('{"detail":"Active membership required"}', 403);
      }));
    await expectLater(client.post('jobs', {}), throwsFormatException);
    expect(mutations, 0);
    client.dispose();
  });

  test('in-flight account change rejects result and never retries mutation', () async {
    var token = 'A'; var mutations = 0;
    final client = ByopService(member: true,
      applicationAuthorization: () async => {'Authorization': 'Bearer $token'},
      client: MockClient((request) async {
        if (request.url.path.endsWith('/session')) return http.Response('{"principal":"member:A"}', 200);
        mutations++; token = 'B'; return http.Response('{"id":"private-A"}', 200);
      }));
    await expectLater(client.post('executions', {}), throwsFormatException);
    expect(mutations, 1);
    client.dispose();
  });

  test('BYOP IDs are principal scoped and failed disconnect retains recovery handle', () async {
    const p1 = 'member:A'; const p2 = 'member:B';
    FlutterSecureStorage.setMockInitialValues({'pollinations_byop_id_$p1': 'credential-A',
      'pollinations_byop_id_$p2': 'credential-B'});
    final session = PollinationsSessionService(
      ownerAuthorization: () async => {'Authorization': 'Bearer member-A'},
      client: MockClient((request) async {
        if (request.url.path.endsWith('/session')) return http.Response('{"principal":"member:A"}', 200);
        expect(request.url.path, '/v1/byop/credentials/credential-A/disconnect');
        return http.Response('{"detail":"Persistence unconfirmed"}', 503);
      }));
    await expectLater(session.disconnectByop(p1), throwsA(isA<PollinationsSessionException>()));
    expect(await session.byopCredentialId(p1), 'credential-A');
    expect(await session.byopCredentialId(p2), 'credential-B');
    await session.dispose();
  });
  test('Cloudflare uses the existing routes with explicit provider and Neurons consent', () async {
    final paths = <String>[];
    final service = ByopService(member: false,
      applicationAuthorization: () async => {'Authorization': 'Bearer owner-offline'},
      client: MockClient((request) async {
        expect(request.url.queryParameters['provider'], 'cloudflare');
        expect(request.headers['Authorization'], 'Bearer owner-offline');
        paths.add(request.url.path);
        if (request.url.path.endsWith('/session')) {
          return http.Response(jsonEncode({'principal': 'owner:fixture',
            'cloudflare_offline_available': true, 'readiness': {'offline_mock_enabled': true}}), 200);
        }
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['maximum_neurons'], 80);
        expect(body.containsKey('maximum_micro_pollen'), isFalse);
        return http.Response('{"consent_id":"offline-consent"}', 200);
      }));
    service.provider = 'cloudflare';
    final response = await service.post('jobs/offline-job/consents', {
      'credential_id': 'A', 'maximum_neurons': 80, 'expires_at': 1200});
    expect(response['consent_id'], 'offline-consent');
    expect(service.cloudflareAvailable, isTrue);
    expect(paths, ['/v1/byop/session', '/v1/byop/jobs/offline-job/consents']);
    service.dispose();
  });

  test('disabled Cloudflare capability fails before any mutation', () async {
    var mutations = 0;
    final service = ByopService(member: false,
      applicationAuthorization: () async => {'Authorization': 'Bearer owner-offline'},
      client: MockClient((request) async {
        if (request.method == 'POST') mutations++;
        return http.Response('{"detail":"Cloudflare offline capability is disabled"}', 503);
      }));
    service.provider = 'cloudflare';
    await expectLater(service.post('executions', {}), throwsFormatException);
    expect(mutations, 0);
    service.dispose();
  });

  test('Cloudflare export preserves provider, auth and approved PNG hash', () async {
    final image = base64Decode('iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAADElEQVR4nGNgGB4AAADIAAGtQHYiAAAAAElFTkSuQmCC');
    final hash = sha256.convert(image).toString();
    final service = ByopService(member: false,
      applicationAuthorization: () async => {'Authorization':'Bearer offline-owner'},
      client: MockClient((request) async {
        expect(request.url.queryParameters['provider'], 'cloudflare');
        expect(request.headers['Authorization'], 'Bearer offline-owner');
        if (request.url.path.endsWith('/session')) {
          return http.Response('{"principal":"owner:fixture","cloudflare_available":true}', 200);
        }
        expect(request.url.path, '/v1/byop/jobs/offline-job/export');
        expect(request.url.queryParameters['format'], 'png');
        return http.Response.bytes(image, 200);
      }));
    service.provider = 'cloudflare';
    expect(await service.exportAsset('offline-job', hash), image);
    expect(service.cloudflareAvailable, isTrue);
    await expectLater(service.exportAsset('offline-job', 'wrong-hash'), throwsFormatException);
    service.dispose();
  });

  test('unapproved export failure does not retry or fall back', () async {
    var exports = 0;
    final service = ByopService(member: false,
      applicationAuthorization: () async => {'Authorization':'Bearer offline-owner'},
      client: MockClient((request) async {
        if (request.url.path.endsWith('/session')) {
          return http.Response('{"principal":"owner:fixture","cloudflare_available":true}', 200);
        }
        exports++;
        expect(request.url.queryParameters['format'], 'zip');
        return http.Response('{"detail":"Exact image approval required"}', 409);
      }));
    service.provider = 'cloudflare';
    await expectLater(service.exportAsset('offline-job', 'hash', zip: true), throwsFormatException);
    expect(exports, 1);
    service.dispose();
  });

}

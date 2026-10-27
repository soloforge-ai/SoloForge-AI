// Mock-only tests intended for CI; Flutter SDK unavailable in local executor.
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/byop_service.dart';
import 'package:frontend/services/pollinations_session_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

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
}

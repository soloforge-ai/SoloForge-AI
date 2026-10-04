import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/soloforge_session_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('account switch during owner bootstrap never returns owner bearer', () async {
    OwnerIdentity? identity = (userId: 'owner', accessToken: 'owner-supabase');
    final entered = Completer<void>();
    final release = Completer<void>();
    final service = SoloForgeSessionService(
      currentIdentity: () => identity,
      client: MockClient((request) async {
        expect(request.headers['Authorization'], 'Bearer owner-supabase');
        entered.complete();
        await release.future;
        return http.Response('{"session_token":"owner-app-token"}', 200);
      }),
    );

    final pending = service.authorizationHeaders();
    await entered.future;
    identity = (userId: 'anonymous', accessToken: 'anonymous-supabase');
    release.complete();
    await expectLater(
      pending,
      throwsA(isA<SoloForgeSessionException>()),
    );
    service.dispose();
  });

  test('signed out and nonowner identities receive no app bearer', () async {
    OwnerIdentity? identity;
    var requests = 0;
    final service = SoloForgeSessionService(
      currentIdentity: () => identity,
      client: MockClient((_) async {
        requests++;
        return http.Response('{"detail":"not owner"}', 403);
      }),
    );
    await expectLater(
      service.authorizationHeaders(),
      throwsA(isA<SoloForgeSessionException>()),
    );
    expect(requests, 0);
    identity = (userId: 'anonymous', accessToken: 'anonymous-supabase');
    await expectLater(
      service.authorizationHeaders(),
      throwsA(isA<SoloForgeSessionException>()),
    );
    expect(requests, 1);
    service.dispose();
  });
}

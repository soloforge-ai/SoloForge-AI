import 'dart:async';
import 'dart:convert';
import 'package:frontend/main.dart';

import 'package:frontend/services/soloforge_session_service.dart';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:frontend/services/owner_v2_session_service.dart';
import 'package:frontend/pages/owner_v2_login_page.dart';

final token = 'sf_owner_v2_${List.filled(43, 'a').join()}';
final proof = List.filled(43, 'b').join();
Map<String, dynamic> get identity => {
  'authenticated': true,
  'identity_version': 'owner_v2',
};

http.Response response(Map<String, dynamic> body, [int status = 200]) =>
    http.Response(jsonEncode(body), status);

Future<void> login(OwnerV2SessionService service) async {
  await service.requestCode('owner@example.test');
  await service.verifyCode(List.filled(43, 'c').join());
}

void main() {
  testWidgets('V2 gate opens independently of Supabase Auth', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: OwnerV2AppGate()));
    expect(find.text('Owner email'), findsOneWidget);
    expect(find.text('Continue with GitHub'), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });

  test(
    'content session bridge selects V2 and never falls back to GitHub',
    () async {
      var status = 200;
      final v2 = OwnerV2SessionService(
        client: MockClient((request) async {
          if (request.url.path.endsWith('/request')) {
            return response({
              'challenge_id': 'id',
              'browser_proof': proof,
            }, 202);
          }
          if (request.url.path.endsWith('/verify')) {
            return response({...identity, 'session_token': token});
          }
          return response(identity, status);
        }),
      );
      final bridge = SoloForgeSessionService(
        ownerV2Session: v2,
        useOwnerV2: true,
        currentIdentity: () =>
            throw StateError('Legacy identity must not be read'),
        client: MockClient(
          (_) async => throw StateError('Legacy bootstrap forbidden'),
        ),
      );
      await login(v2);
      expect(await bridge.authorizationHeaders(), {
        'Authorization': 'Bearer $token',
      });
      status = 401;
      await expectLater(
        bridge.authorizationHeaders(),
        throwsA(isA<SoloForgeSessionException>()),
      );
      expect(v2.authenticated, isFalse);
      bridge.dispose();
      v2.dispose();
    },
  );

  test(
    'request, verify, session validation, logout; no secrets in URLs',
    () async {
      final paths = <String>[];
      final service = OwnerV2SessionService(
        client: MockClient((request) async {
          expect(request.url.query, isEmpty);
          paths.add(request.url.path);
          switch (request.url.path.split('/').last) {
            case 'request':
              expect(jsonDecode(request.body)['email'], 'owner@example.test');
              return response({
                'challenge_id': '11111111-1111-4111-8111-111111111111',
                'browser_proof': proof,
              }, 202);
            case 'verify':
              expect(jsonDecode(request.body)['browser_proof'], proof);
              return response({...identity, 'session_token': token});
            case 'session':
              expect(request.headers['Authorization'], 'Bearer $token');
              return response(identity);
            case 'logout':
              expect(request.headers['Authorization'], 'Bearer $token');
              return http.Response('', 204);
          }
          throw StateError('Unexpected request');
        }),
      );
      await login(service);
      expect(service.authenticated, isTrue);
      expect(await service.authorizationHeaders(), {
        'Authorization': 'Bearer $token',
      });
      await service.logout();
      expect(service.authenticated, isFalse);
      await expectLater(
        service.authorizationHeaders(),
        throwsA(isA<OwnerV2Exception>()),
      );
      expect(paths.length, 4);
      service.dispose();
    },
  );

  test(
    'revocation or infrastructure failure clears session without fallback',
    () async {
      for (final status in [401, 503]) {
        final service = OwnerV2SessionService(
          client: MockClient((request) async {
            if (request.url.path.endsWith('/request')) {
              return response({
                'challenge_id': 'id',
                'browser_proof': proof,
              }, 202);
            }
            if (request.url.path.endsWith('/verify')) {
              return response({...identity, 'session_token': token});
            }
            return response({'detail': 'private error'}, status);
          }),
        );
        await login(service);
        await expectLater(
          service.authorizationHeaders(),
          throwsA(isA<OwnerV2Exception>()),
        );
        expect(service.authenticated, isFalse);
        service.dispose();
      }
    },
  );

  test('logout invalidates an in-flight verify response', () async {
    final entered = Completer<void>();
    final released = Completer<void>();
    final service = OwnerV2SessionService(
      client: MockClient((request) async {
        if (request.url.path.endsWith('/request')) {
          return response({'challenge_id': 'id', 'browser_proof': proof}, 202);
        }
        entered.complete();
        await released.future;
        return response({...identity, 'session_token': token});
      }),
    );
    await service.requestCode('owner@example.test');
    final pending = service.verifyCode(proof);
    await entered.future;
    await service.logout();
    released.complete();
    await pending;
    expect(service.authenticated, isFalse);
    service.dispose();
  });

  test('ambiguous verify cannot automatically reuse challenge', () async {
    var verifies = 0;
    final service = OwnerV2SessionService(
      client: MockClient((request) async {
        if (request.url.path.endsWith('/request')) {
          return response({'challenge_id': 'id', 'browser_proof': proof}, 202);
        }
        verifies++;
        throw Exception('network');
      }),
    );
    await service.requestCode('owner@example.test');
    await expectLater(
      service.verifyCode(proof),
      throwsA(isA<OwnerV2Exception>()),
    );
    await expectLater(
      service.verifyCode(proof),
      throwsA(isA<OwnerV2Exception>()),
    );
    expect(verifies, 1);
    service.dispose();
  });

  testWidgets('email login presents generic delivery and code field', (
    tester,
  ) async {
    final service = OwnerV2SessionService(
      client: MockClient(
        (request) async =>
            response({'challenge_id': 'id', 'browser_proof': proof}, 202),
      ),
    );
    await tester.pumpWidget(
      MaterialApp(home: OwnerV2LoginPage(sessions: service)),
    );
    await tester.enterText(find.byType(TextField), 'owner@example.test');
    await tester.tap(find.text('Send email code'));
    await tester.pumpAndSettle();
    expect(find.textContaining('If this email is registered'), findsOneWidget);
    expect(find.text('Email code (43 characters)'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    service.dispose();
  });
}

import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:frontend/pages/pollinations_account_inspect_page.dart';
import 'package:frontend/services/soloforge_session_service.dart';

import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/pollinations_session_service.dart';
import 'package:frontend/services/prawtwan_language.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

PollinationsSessionService sessionService({http.Client? client}) =>
    PollinationsSessionService(
      client:
          client ??
          MockClient(
            (request) async => http.Response(
              '{"launch_path":"/auth/pollinations/launch?ticket=offline"}',
              200,
            ),
          ),
      ownerAuthorization: () async => {'Authorization': 'Bearer owner-v2-test'},
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const key = 'pollinations_session_token';
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  for (final status in [401, 403, 404]) {
    test('owner denial $status preserves handle without authenticating it', () async {
      FlutterSecureStorage.setMockInitialValues({key: 'retained-provider'});
      var ownerRestored = false;
      var launches = 0;
      http.Client client() => MockClient((request) async {
        if (!request.url.path.endsWith('/status')) launches++;
        return ownerRestored
            ? http.Response('{"connected":true,"spending_authorized":false}', 200)
            : http.Response('{"detail":"Owner authorization required"}', status);
      });
      final beforeRestart = sessionService(client: client());
      await expectLater(beforeRestart.status(), throwsA(isA<PollinationsSessionException>()));
      await expectLater(beforeRestart.connect(), throwsA(isA<PollinationsSessionException>()));
      expect(await beforeRestart.readSessionToken(), 'retained-provider');
      expect(launches, 0);
      await beforeRestart.dispose();
      final restarted = sessionService(client: client());
      await expectLater(restarted.status(), throwsA(isA<PollinationsSessionException>()));
      ownerRestored = true;
      expect((await restarted.status()).connected, isTrue);
      expect(await restarted.readSessionToken(), 'retained-provider');
      await restarted.dispose();
    });
  }

  for (final reason in ['expired', 'revoked']) {
    test('confirmed provider $reason clears handle and permits fresh handoff', () async {
      FlutterSecureStorage.setMockInitialValues({key: reason});
      final session = sessionService(client: MockClient((request) async {
        if (request.url.path.endsWith('/status')) {
          return http.Response('{"connected":false}', 200);
        }
        return http.Response('{"session_token":"new-$reason"}', 200);
      }));
      expect((await session.status()).connected, isFalse);
      expect(await session.readSessionToken(), isNull);
      expect((await session.restoreCallbackCode('reconnect-$reason')).connected, isTrue);
      expect(await session.readSessionToken(), 'new-$reason');
      await session.dispose();
    });
  }

  test('local Owner sign-in failure preserves provider handle and sends nothing', () async {
    FlutterSecureStorage.setMockInitialValues({key: 'retained'});
    var requests = 0;
    final session = PollinationsSessionService(
      ownerAuthorization: () async => throw const SoloForgeSessionException('Sign in required'),
      client: MockClient((_) async { requests++; return http.Response('{}', 200); }),
    );
    await expectLater(session.status(), throwsA(isA<SoloForgeSessionException>()));
    expect(await session.readSessionToken(), 'retained');
    expect(requests, 0);
    await session.dispose();
  });

  for (final token in ['valid', 'expired', 'forged', 'mismatched']) {
    test('$token stored session is validated before callback restoration', () async {
      FlutterSecureStorage.setMockInitialValues({key: token});
      var exchanges = 0;
      final session = sessionService(
        client: MockClient((request) async {
          if (request.url.path.endsWith('/status')) {
            return http.Response(
              '{"connected":${request.headers['X-Pollinations-Session'] == 'valid' || request.headers['X-Pollinations-Session'] == 'restored'}}',
              200,
            );
          }
          exchanges++;
          return http.Response('{"session_token":"restored"}', 200);
        }),
      );
      expect(
        (await session.restoreCallbackCode('restore-$token')).connected,
        isTrue,
      );
      expect(exchanges, token == 'valid' ? 0 : 1);
      expect(
        await session.readSessionToken(),
        token == 'valid' ? 'valid' : 'restored',
      );
      await session.dispose();
    });
  }

  test(
    'two page instances exchange a callback once; replay uses current status',
    () async {
      final reply = Completer<http.Response>();
      var calls = 0;
      http.Client client() => MockClient((request) async {
        if (request.url.path.endsWith('/status')) {
          return http.Response('{"connected":true}', 200);
        }
        calls++;
        return reply.future;
      });
      final image = sessionService(client: client());
      final chat = sessionService(client: client());
      final a = image.restoreCallbackCode('shared-code');
      final b = chat.restoreCallbackCode('shared-code');
      await Future<void>.delayed(Duration.zero);
      expect(calls, 1);
      reply.complete(http.Response('{"session_token":"shared"}', 200));
      expect((await a).connected, isTrue);
      expect((await b).connected, isTrue);
      expect(
        await image.authorizationHeaders(),
        await chat.authorizationHeaders(),
      );
      expect((await chat.restoreCallbackCode('shared-code')).connected, isTrue);
      expect(calls, 1);
      FlutterSecureStorage.setMockInitialValues({});
      expect(
        (await chat.restoreCallbackCode('shared-code')).connected,
        isFalse,
      );
      expect(calls, 1); // cached callback cannot restore a logged-out session
      await image.dispose();
      await chat.dispose();
    },
  );

  test('stale status cannot delete a callback replacement token', () async {
    FlutterSecureStorage.setMockInitialValues({key: 'old'});
    final stale = Completer<http.Response>();
    final image = sessionService(
      client: MockClient(
        (request) => request.headers['X-Pollinations-Session'] == 'old'
            ? stale.future
            : Future.value(http.Response('{"connected":true}', 200)),
      ),
    );
    final chat = sessionService(
      client: MockClient((request) async {
        if (request.url.path.endsWith('/status')) {
          return http.Response(
            '{"connected":${request.headers['X-Pollinations-Session'] == 'new'}}',
            200,
          );
        }
        return http.Response('{"session_token":"new"}', 200);
      }),
    );
    final check = image.status();
    await Future<void>.delayed(Duration.zero);
    expect((await chat.restoreCallbackCode('race-code')).connected, isTrue);
    stale.complete(http.Response('{"connected":false}', 200));
    await check;
    expect(await chat.readSessionToken(), 'new');
    await image.dispose();
    await chat.dispose();
  });

  test(
    'transient status failure preserves token and prevents login launch',
    () async {
      FlutterSecureStorage.setMockInitialValues({key: 'existing'});
      final session = sessionService(
        client: MockClient((_) async => http.Response('{}', 503)),
      );
      await expectLater(
        session.connect(),
        throwsA(isA<PollinationsSessionException>()),
      );
      expect(await session.readSessionToken(), 'existing');
      await session.dispose();
    },
  );

  test('failed handoff is not automatically retried by another page', () async {
    var calls = 0;
    final session = sessionService(
      client: MockClient((_) async {
        calls++;
        return http.Response('{"detail":"Ambiguous exchange"}', 502);
      }),
    );
    await expectLater(
      session.restoreCallbackCode('failed-code'),
      throwsA(isA<PollinationsSessionException>()),
    );
    expect(
      (await session.restoreCallbackCode('failed-code')).connected,
      isFalse,
    );
    expect(calls, 1);
    await session.dispose();
  });

  test('forged handoff response never installs a session', () async {
    var calls = 0;
    final session = sessionService(
      client: MockClient((request) async {
        calls++;
        expect(request.url.path, '/auth/pollinations/mobile/exchange');
        return http.Response(
          '{"detail":"Invalid or expired mobile handoff code"}',
          400,
        );
      }),
    );
    await expectLater(
      session.handleCallback(
        Uri.parse('soloforge://oauth/pollinations?code=forged-handoff'),
      ),
      throwsA(isA<PollinationsSessionException>()),
    );
    expect(await session.readSessionToken(), isNull);
    expect(calls, 1);
    await session.dispose();
  });

  test('wrong callback URL cannot exchange a code', () async {
    var calls = 0;
    final session = sessionService(
      client: MockClient((_) async {
        calls++;
        return http.Response('{}', 200);
      }),
    );
    await expectLater(
      session.handleCallback(
        Uri.parse('evil://oauth/pollinations?code=forged'),
      ),
      throwsA(isA<PollinationsSessionException>()),
    );
    expect(calls, 0);
    await session.dispose();
  });

  test('concurrent login requests launch once across instances', () async {
    final launched = Completer<bool>();
    var calls = 0;
    const channel = MethodChannel('plugins.flutter.io/url_launcher');
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (_) {
          calls++;
          return launched.future;
        });
    addTearDown(
      () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null),
    );
    final image = sessionService();
    final chat = sessionService();
    final a = image.connect();
    final b = chat.connect();
    await Future<void>.delayed(Duration.zero);
    expect(calls, 1);
    launched.complete(true);
    await Future.wait([a, b]);
    await image.dispose();
    await chat.dispose();
  });

  test('valid shared session never opens login', () async {
    FlutterSecureStorage.setMockInitialValues({key: 'valid'});
    final session = sessionService(
      client: MockClient((request) async {
        expect(request.url.path, '/auth/pollinations/status');
        return http.Response('{"connected":true}', 200);
      }),
    );
    await session.connect();
    await session.dispose();
  });

  test(
    'authenticated disconnected status clears an unavailable provider handle',
    () async {
      FlutterSecureStorage.setMockInitialValues({key: 'unbound-legacy'});
      final session = sessionService(
        client: MockClient((_) async => http.Response('{"connected":false}', 200)),
      );
      expect((await session.status()).connected, isFalse);
      expect(await session.readSessionToken(), isNull);
      await session.dispose();
    },
  );

  test('owner bearer and provider session remain separate', () async {
    FlutterSecureStorage.setMockInitialValues({key: 'provider-handle'});
    final session = sessionService(
      client: MockClient((request) async {
        expect(request.headers['Authorization'], 'Bearer owner-v2-test');
        expect(request.headers['X-Pollinations-Session'], 'provider-handle');
        return http.Response(
          '{"connected":true,"spending_authorized":false}',
          200,
        );
      }),
    );
    expect((await session.status()).connected, isTrue);
    await session.dispose();
  });

  testWidgets(
    'owner login, submit Pending, reverify and inspect are connected',
    (tester) async {
      String? state;
      var ownerRequests = 0;
      var submits = 0;
      var verifies = 0;
      final ownerToken = 'sf_owner_v2_${List.filled(43, 'a').join()}';
      final ownerService = SoloForgeSessionService(
        useOwnerV2: true,
        currentIdentity: () =>
            (userId: 'github-owner', accessToken: 'github-proof'),
        client: MockClient((request) async {
          ownerRequests++;
          if (request.url.path.endsWith('/bootstrap-v2')) {
            expect(request.headers['Authorization'], 'Bearer github-proof');
            return http.Response(
              jsonEncode({
                'session_token': ownerToken,
                'authenticated': true,
                'identity_version': 'owner_v2',
              }),
              200,
            );
          }
          expect(request.url.path, '/auth/owner-v2/session');
          expect(request.headers['Authorization'], 'Bearer $ownerToken');
          return http.Response(
            '{"authenticated":true,"identity_version":"owner_v2"}',
            200,
          );
        }),
      );
      final client = MockClient((request) async {
        expect(request.headers['Authorization'], 'Bearer $ownerToken');
        switch (request.url.path) {
          case '/auth/pollinations/account/credentials':
            return http.Response(
              jsonEncode({
                'credentials': state == null
                    ? []
                    : [
                        {'id': 'record-1', 'verification_status': state},
                      ],
              }),
              200,
            );
          case '/auth/pollinations/sk/submit':
            submits++;
            expect(jsonDecode(request.body), {
              'access_token': 'sk_offline_widget',
            });
            state = 'PENDING_VERIFICATION';
            return http.Response(
              '{"verification_status":"PENDING_VERIFICATION","provider_ownership_verified":false,"spending_authorized":false}',
              200,
            );
          case '/auth/pollinations/sk/reverify':
            verifies++;
            expect(jsonDecode(request.body), {
              'credential_record_id': 'record-1',
            });
            state = 'VERIFIED';
            return http.Response(
              '{"verification_status":"VERIFIED","provider_ownership_verified":true,"spending_authorized":false}',
              200,
            );
          case '/auth/pollinations/account/inspect':
            expect(
              request.url.queryParameters['credential_record_id'],
              'record-1',
            );
            return http.Response(
              '{"verification_status":"VERIFIED","owner_binding":"VERIFIED","provider_ownership_verified":true,"spending_authorized":false,"provider_subject":"provider-owner","evidence":{}}',
              200,
            );
          default:
            throw StateError('Unexpected endpoint');
        }
      });
      await tester.pumpWidget(
        MaterialApp(
          home: PollinationsAccountInspectPage(
            client: client,
            ownerAuthorization: ownerService.authorizationHeaders,
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('No active stored credentials loaded.'), findsOneWidget);
      await tester.tap(find.text('Submit or claim existing SK'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField).at(1), 'sk_offline_widget');
      await tester.tap(find.widgetWithText(TextButton, 'Claim'));
      await tester.pumpAndSettle();
      expect(submits, 1);
      expect(find.text('State: PENDING_VERIFICATION'), findsOneWidget);
      await tester.ensureVisible(find.text('Verify provider ownership'));
      await tester.tap(find.text('Verify provider ownership'));
      await tester.pumpAndSettle();
      expect(verifies, 1);
      expect(find.text('State: VERIFIED'), findsOneWidget);
      expect(find.text('Owner binding: VERIFIED'), findsOneWidget);
      await tester.ensureVisible(find.text('Inspect existing account'));
      await tester.tap(find.text('Inspect existing account'));
      await tester.pumpAndSettle();
      expect(find.text('Provider subject: provider-owner'), findsOneWidget);
      expect(find.text('Spending authorized: No'), findsOneWidget);
      expect(ownerRequests, greaterThan(1));
      await tester.pumpWidget(const SizedBox.shrink());
      ownerService.dispose();
    },
  );

  testWidgets('owner authorization failure makes no credential request', (
    tester,
  ) async {
    var calls = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: PollinationsAccountInspectPage(
          client: MockClient((_) async {
            calls++;
            return http.Response('{}', 200);
          }),
          ownerAuthorization: () async =>
              throw const SoloForgeSessionException('Owner sign-in required'),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(calls, 0);
    expect(find.textContaining('Owner sign-in required'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  test('authorization failures do not tell connected users to login again', () {
    for (final language in ['th', 'en']) {
      final copy = PrawtwanCopy(language);
      expect(
        copy.error(
          'Generation execution is locked pending verified owner and spending authorization.',
        ),
        copy.privacy,
      );
      expect(copy.error('Chat Prawtwan failed (403).'), isNot(copy.connect));
      expect(copy.error('Chat Prawtwan failed (401).'), copy.connect);
    }
  });
}

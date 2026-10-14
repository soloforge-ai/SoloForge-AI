import 'dart:async';

import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/pollinations_session_service.dart';
import 'package:frontend/services/prawtwan_language.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const key = 'pollinations_session_token';
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  for (final token in ['valid', 'expired', 'forged', 'mismatched']) {
    test(
      '$token stored session is validated before callback restoration',
      () async {
        FlutterSecureStorage.setMockInitialValues({key: token});
        var exchanges = 0;
        final session = PollinationsSessionService(
          client: MockClient((request) async {
            if (request.url.path.endsWith('/status')) {
              return http.Response(
                '{"connected":${request.headers['Authorization'] == 'Bearer valid' || request.headers['Authorization'] == 'Bearer restored'}}',
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
      },
    );
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
      final image = PollinationsSessionService(client: client());
      final chat = PollinationsSessionService(client: client());
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
    final image = PollinationsSessionService(
      client: MockClient(
        (request) => request.headers['Authorization'] == 'Bearer old'
            ? stale.future
            : Future.value(http.Response('{"connected":true}', 200)),
      ),
    );
    final chat = PollinationsSessionService(
      client: MockClient((request) async {
        if (request.url.path.endsWith('/status')) {
          return http.Response(
            '{"connected":${request.headers['Authorization'] == 'Bearer new'}}',
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
      final session = PollinationsSessionService(
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
    final session = PollinationsSessionService(
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
    final session = PollinationsSessionService(
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
    final session = PollinationsSessionService(
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
    final image = PollinationsSessionService();
    final chat = PollinationsSessionService();
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
    final session = PollinationsSessionService(
      client: MockClient((request) async {
        expect(request.url.path, '/auth/pollinations/status');
        return http.Response('{"connected":true}', 200);
      }),
    );
    await session.connect();
    await session.dispose();
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

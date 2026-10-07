import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/pages/home_page.dart';
import 'package:frontend/pages/prawtwan_chat_page.dart';
import 'package:frontend/services/prawtwan_chat_service.dart';
import 'package:frontend/services/prawtwan_language.dart';
import 'package:frontend/services/pollinations_session_service.dart';

class FakeChat extends PrawtwanChatService {
  final reply = Completer<String>();
  List<PrawtwanMessage>? sent;
  int calls = 0;
  @override
  Future<String> send(List<PrawtwanMessage> messages) {
    calls++;
    sent = messages;
    return reply.future;
  }
}

class FakeSession extends PollinationsSessionService {
  @override
  Future<Map<String, String>> authorizationHeaders() async => {
    'Authorization': 'Bearer existing-session',
  };
}

void main() {
  test(
    'existing endpoint, authorization and message contract are retained',
    () async {
      final service = PrawtwanChatService(
        sessionService: FakeSession(),
        client: MockClient((request) async {
          expect(request.url.path, '/v1/prawtwan/chat');
          expect(request.headers['Authorization'], 'Bearer existing-session');
          expect(jsonDecode(request.body), {
            'messages': [
              {'role': 'user', 'content': 'My scene'},
            ],
          });
          return http.Response('{"message":"Feedback"}', 200);
        }),
      );
      expect(
        await service.send([
          const PrawtwanMessage(role: 'user', content: 'My scene'),
        ]),
        'Feedback',
      );
      await service.dispose();
    },
  );
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  Future<void> open(WidgetTester tester, {FakeChat? service}) async {
    await tester.pumpWidget(
      MaterialApp(home: PrawtwanChatPage(service: service)),
    );
    await tester.pumpAndSettle();
  }

  Future<void> choose(WidgetTester tester, String label) async {
    await tester.tap(find.byType(DropdownButton<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text(label).last);
    await tester.pumpAndSettle();
  }

  testWidgets('Home prominently opens the existing chat page', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: HomePage()));
    await tester.pump();
    expect(find.text('Test PRAWTWAN'), findsNothing);
    await tester.tap(find.text('Prawtwan · พี่พราว'));
    await tester.pumpAndSettle();
    expect(find.byType(PrawtwanChatPage), findsOneWidget);
  });

  testWidgets('Thai device default, English switch, persistence and clear', (
    tester,
  ) async {
    tester.binding.platformDispatcher.localeTestValue = const Locale(
      'th',
      'TH',
    );
    addTearDown(tester.binding.platformDispatcher.clearLocaleTestValue);
    final service = FakeChat();
    await open(tester, service: service);
    expect(find.text('คุยกับพี่พราว'), findsOneWidget);
    expect(find.text('พี่พราวพร้อมแล้ว'), findsOneWidget);
    expect(service.sent, isNull);
    await choose(tester, 'English');
    expect(find.text('Chat with Prawtwan'), findsOneWidget);
    expect(find.text('Fiction editor'), findsOneWidget);
    expect(find.text('Prawtwan is ready'), findsOneWidget);
    expect(find.byTooltip('Send message'), findsOneWidget);
    expect(await PrawtwanLanguagePreference().read(), 'en');
    await tester.enterText(find.byType(TextField), 'My scene');
    await tester.tap(find.byType(FilledButton));
    await tester.pump();
    expect(find.text('Prawtwan is reading...'), findsOneWidget);
    await tester.tap(find.byType(DropdownButton<String>));
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('ไทย').last);
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('พี่พราวกำลังอ่าน...'), findsOneWidget);
    service.reply.complete('Scene feedback');
    await tester.pumpAndSettle();
    expect(service.sent!.single.content, 'My scene');
    expect(find.text('Scene feedback'), findsOneWidget);
    await tester.tap(find.byTooltip('ล้างบทสนทนา'));
    await tester.pumpAndSettle();
    expect(find.text('พี่พราวพร้อมแล้ว'), findsOneWidget);
    await choose(tester, 'English');
    await tester.pumpWidget(const SizedBox());
    await open(tester);
    expect(find.text('Chat with Prawtwan'), findsOneWidget);
  });

  testWidgets('unsupported device locale falls back to English', (
    tester,
  ) async {
    tester.binding.platformDispatcher.localeTestValue = const Locale('fr');
    addTearDown(tester.binding.platformDispatcher.clearLocaleTestValue);
    FlutterSecureStorage.setMockInitialValues({
      PrawtwanLanguagePreference.key: 'bad',
    });
    await open(tester);
    expect(find.text('Chat with Prawtwan'), findsOneWidget);
  });

  testWidgets('Thai saved choice overrides English device on narrow screen', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(360, 720);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    FlutterSecureStorage.setMockInitialValues({
      PrawtwanLanguagePreference.key: 'th',
    });
    await open(tester);
    expect(find.text('คุยกับพี่พราว'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  for (final error in [
    const PollinationsSessionException(
      'Connect Pollinations before generating assets.',
    ),
    const PrawtwanChatException('Prawtwan did not respond in time.'),
    const PrawtwanChatException('Prawtwan returned an invalid response.'),
    const PrawtwanChatException('The chat context is too large.'),
    Exception('private upstream details'),
  ]) {
    testWidgets('localizes error ${error.runtimeType}: $error', (tester) async {
      FlutterSecureStorage.setMockInitialValues({
        PrawtwanLanguagePreference.key: 'th',
      });
      final service = FakeChat();
      await open(tester, service: service);
      await tester.enterText(find.byType(TextField), 'ฉาก');
      await tester.tap(find.byType(FilledButton));
      await tester.pump();
      service.reply.completeError(error);
      await tester.pumpAndSettle();
      final copy = const PrawtwanCopy('th');
      expect(
        find.text(
          error is PollinationsSessionException
              ? copy.connect
              : error is PrawtwanChatException
              ? copy.error(error.message)
              : copy.unavailable,
        ),
        findsOneWidget,
      );
      expect(find.text('ฉาก'), findsOneWidget);
      expect(find.text('private upstream details'), findsNothing);
      expect(tester.widget<TextField>(find.byType(TextField)).enabled, isTrue);
    });
  }
}

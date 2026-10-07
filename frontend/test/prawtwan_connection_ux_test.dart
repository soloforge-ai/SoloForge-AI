import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/pages/prawtwan_chat_page.dart';
import 'package:frontend/services/pollinations_session_service.dart';
import 'package:frontend/services/prawtwan_chat_service.dart';
import 'package:frontend/services/prawtwan_language.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

class TestSession extends PollinationsSessionService {
  TestSession({this.connected = false});
  bool connected;
  bool failConnect = false;
  int connections = 0;
  Completer<void>? pendingConnect;
  int callbacks = 0;
  Future<void> Function(Uri)? callback;
  Completer<PollinationsSessionState>? pendingStatus;
  Completer<PollinationsSessionState>? pendingCallback;

  @override
  Future<PollinationsSessionState> status() async => pendingStatus != null
      ? pendingStatus!.future
      : PollinationsSessionState(connected: connected);
  @override
  Future<void> startListening({
    required Future<void> Function(Uri) onCallback,
  }) async {
    callback = onCallback;
  }

  @override
  Future<void> connect() async {
    connections++;
    if (pendingConnect != null) await pendingConnect!.future;
    if (failConnect) throw const PollinationsSessionException('private error');
  }

  @override
  Future<PollinationsSessionState> handleCallback(Uri uri) async {
    callbacks++;
    if (pendingCallback != null) return pendingCallback!.future;
    connected = true;
    return const PollinationsSessionState(connected: true);
  }
}

class ImmediateChat extends PrawtwanChatService {
  int calls = 0;
  @override
  Future<String> send(List<PrawtwanMessage> messages) async {
    calls++;
    return 'Feedback';
  }
}

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  Future<void> open(
    WidgetTester tester,
    TestSession session, {
    String language = 'en',
    ImmediateChat? chat,
    Map<String, dynamic>? restored,
  }) async {
    FlutterSecureStorage.setMockInitialValues({
      PrawtwanLanguagePreference.key: language,
    });
    await tester.pumpWidget(
      MaterialApp(
        home: PrawtwanChatPage(
          sessionService: session,
          service: chat ?? ImmediateChat(),
          restored: restored,
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  for (final entry in {
    'en': 'Connect Pollinations',
    'th': 'เชื่อมต่อ Pollinations',
  }.entries) {
    testWidgets(
      'disconnected ${entry.key} shows localized CTA and starts existing service',
      (tester) async {
        final session = TestSession();
        await open(tester, session, language: entry.key);
        expect(find.text(entry.value), findsOneWidget);
        expect(
          tester
              .widget<FilledButton>(find.byKey(const ValueKey('prawtwan-send')))
              .onPressed,
          isNull,
        );
        await tester.enterText(find.byType(TextField), 'Draft scene');
        await tester.tap(find.byKey(const ValueKey('prawtwan-connect')));
        await tester.pumpAndSettle();
        expect(session.connections, 1);
        expect(
          tester.widget<TextField>(find.byType(TextField)).controller!.text,
          'Draft scene',
        );
        expect(await PrawtwanLanguagePreference().read(), entry.key);
      },
    );
  }

  testWidgets(
    'CTA launches the unchanged OAuth login URL through the real service',
    (tester) async {
      final launched = <String>[];
      const channel = MethodChannel('plugins.flutter.io/url_launcher');
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(channel, (
        call,
      ) async {
        if (call.arguments is Map && (call.arguments as Map)['url'] is String) {
          launched.add((call.arguments as Map)['url'] as String);
        }
        return true;
      });
      addTearDown(
        () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
          channel,
          null,
        ),
      );
      final session = ListeningSession();
      await tester.pumpWidget(
        MaterialApp(
          home: PrawtwanChatPage(
            sessionService: session,
            service: ImmediateChat(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('prawtwan-connect')));
      await tester.pumpAndSettle();
      expect(launched, hasLength(1));
      final uri = Uri.parse(launched.single);
      expect(uri.path, '/auth/pollinations/login');
      expect(uri.queryParameters, {
        'client': 'mobile',
        'return_to': 'soloforge://oauth/pollinations',
      });
    },
  );

  testWidgets(
    'repeated CTA taps launch once and preserve draft while connecting',
    (tester) async {
      final session = TestSession()..pendingConnect = Completer<void>();
      await open(tester, session);
      await tester.enterText(find.byType(TextField), 'Draft');
      await tester.tap(find.byKey(const ValueKey('prawtwan-connect')));
      await tester.tap(find.byKey(const ValueKey('prawtwan-connect')));
      await tester.pump();
      expect(session.connections, 1);
      expect(tester.widget<TextField>(find.byType(TextField)).enabled, isFalse);
      expect(
        tester
            .widget<DropdownButton<String>>(find.byType(DropdownButton<String>))
            .onChanged,
        isNull,
      );
      session.pendingConnect!.complete();
      await tester.pumpAndSettle();
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'Draft',
      );
    },
  );

  testWidgets('connected state has no connection UI', (tester) async {
    await open(tester, TestSession(connected: true));
    expect(find.byKey(const ValueKey('prawtwan-connect')), findsNothing);
    expect(
      tester
          .widget<FilledButton>(find.byKey(const ValueKey('prawtwan-send')))
          .onPressed,
      isNotNull,
    );
  });

  testWidgets(
    'callback enables chat without leaving page or changing messages/language',
    (tester) async {
      final session = TestSession(connected: true);
      final chat = ImmediateChat();
      await open(tester, session, chat: chat);
      await tester.enterText(find.byType(TextField), 'First scene');
      await tester.tap(find.byKey(const ValueKey('prawtwan-send')));
      await tester.pumpAndSettle();
      await tester.tap(find.byType(DropdownButton<String>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('ไทย').last);
      await tester.pumpAndSettle();
      session.connected = false;
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'Next scene');
      await tester.tap(find.byKey(const ValueKey('prawtwan-connect')));
      await tester.pumpAndSettle();
      await session.callback!(
        Uri.parse('soloforge://oauth/pollinations?code=test'),
      );
      await tester.pumpAndSettle();
      expect(session.callbacks, 1);
      expect(find.byType(PrawtwanChatPage), findsOneWidget);
      expect(find.byKey(const ValueKey('prawtwan-connect')), findsNothing);
      expect(find.text('คุยกับพี่พราว'), findsOneWidget);
      expect(find.text('First scene'), findsOneWidget);
      expect(find.text('Feedback'), findsOneWidget);
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'Next scene',
      );
      await tester.tap(find.byKey(const ValueKey('prawtwan-send')));
      await tester.pumpAndSettle();
      expect(chat.calls, 2);
      expect(find.text('Next scene'), findsOneWidget);
    },
  );

  testWidgets('resume with restored session enables chat immediately', (
    tester,
  ) async {
    final session = TestSession();
    await open(tester, session);
    session.connected = true;
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('prawtwan-connect')), findsNothing);
    expect(
      tester
          .widget<FilledButton>(find.byKey(const ValueKey('prawtwan-send')))
          .onPressed,
      isNotNull,
    );
  });

  testWidgets('stale status and resume cannot overwrite successful callback', (
    tester,
  ) async {
    final session = TestSession();
    await open(tester, session);
    final stale = Completer<PollinationsSessionState>();
    session.pendingStatus = stale;
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    session.pendingCallback = Completer<PollinationsSessionState>();
    final callback = session.callback!(
      Uri.parse('soloforge://oauth/pollinations?code=test'),
    );
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    session.pendingCallback!.complete(
      const PollinationsSessionState(connected: true),
    );
    await callback;
    stale.complete(const PollinationsSessionState(connected: false));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('prawtwan-connect')), findsNothing);
  });

  testWidgets(
    'redirect snapshot restores messages, draft and selected language',
    (tester) async {
      await open(
        tester,
        TestSession(connected: true),
        restored: {
          'language': 'th',
          'draft': 'Unsent scene',
          'messages': [
            {'role': 'user', 'content': 'Saved scene'},
            {'role': 'assistant', 'content': 'Saved feedback'},
          ],
        },
      );
      expect(find.text('คุยกับพี่พราว'), findsOneWidget);
      expect(find.text('Saved scene'), findsOneWidget);
      expect(find.text('Saved feedback'), findsOneWidget);
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'Unsent scene',
      );
    },
  );

  testWidgets('connection failure is localized and can be retried', (
    tester,
  ) async {
    final session = TestSession()..failConnect = true;
    await open(tester, session, language: 'th');
    await tester.tap(find.byKey(const ValueKey('prawtwan-connect')));
    await tester.pumpAndSettle();
    expect(find.text(const PrawtwanCopy('th').connectionError), findsOneWidget);
    expect(find.text('private error'), findsNothing);
    session.failConnect = false;
    await tester.tap(find.byKey(const ValueKey('prawtwan-connect')));
    await tester.pumpAndSettle();
    expect(session.connections, 2);
  });

  testWidgets(
    'existing service exchanges callback and authorizes chat through stored session',
    (tester) async {
      final requests = <String>[];
      final session = ListeningSession(
        client: MockClient((request) async {
          requests.add(request.url.path);
          if (request.url.path.endsWith('/exchange')) {
            return http.Response(
              '{"session_token":"session","expires_at":9999999999}',
              200,
            );
          }
          return http.Response('{"connected":true}', 200);
        }),
      );
      final chat = PrawtwanChatService(
        sessionService: PollinationsSessionService(),
        client: MockClient((request) async {
          expect(request.url.path, '/v1/prawtwan/chat');
          expect(request.headers['Authorization'], 'Bearer session');
          return http.Response('{"message":"Real service reply"}', 200);
        }),
      );
      await tester.pumpWidget(
        MaterialApp(
          home: PrawtwanChatPage(sessionService: session, service: chat),
        ),
      );
      await tester.pumpAndSettle();
      await session.callback!(
        Uri.parse('soloforge://oauth/pollinations?code=handoff'),
      );
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'Scene');
      await tester.tap(find.byKey(const ValueKey('prawtwan-send')));
      await tester.pumpAndSettle();
      expect(find.text('Real service reply'), findsOneWidget);
      expect(requests.where((path) => path.endsWith('/exchange')).length, 1);
    },
  );
}

class ListeningSession extends PollinationsSessionService {
  ListeningSession({super.client});
  Future<void> Function(Uri)? callback;
  @override
  Future<void> startListening({
    required Future<void> Function(Uri) onCallback,
  }) async {
    callback = onCallback;
  }
}

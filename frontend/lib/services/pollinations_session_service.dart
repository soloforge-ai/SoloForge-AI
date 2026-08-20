import 'dart:async';
import 'dart:convert';

import 'package:app_links/app_links.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

const String assetForgeApiUrl = String.fromEnvironment(
  'ASSET_FORGE_API_URL',
  defaultValue: 'https://soloforge-asset-forge.onrender.com',
);

class PollinationsSessionState {
  const PollinationsSessionState({
    required this.connected,
    this.expiresAt,
    this.scope,
  });

  final bool connected;
  final int? expiresAt;
  final String? scope;
}

class PollinationsSessionService {
  PollinationsSessionService({
    http.Client? client,
    FlutterSecureStorage? storage,
    AppLinks? appLinks,
  })  : _client = client ?? http.Client(),
        _storage = storage ?? const FlutterSecureStorage(),
        _appLinks = appLinks ?? AppLinks();

  static const _sessionKey = 'pollinations_session_token';
  static const _returnTo = 'soloforge://oauth/pollinations';

  final http.Client _client;
  final FlutterSecureStorage _storage;
  final AppLinks _appLinks;
  StreamSubscription<Uri>? _linkSubscription;

  String get _baseUrl => assetForgeApiUrl.trim().replaceFirst(RegExp(r'/$'), '');

  Future<String?> readSessionToken() => _storage.read(key: _sessionKey);

  Future<void> startListening({
    required Future<void> Function(Uri uri) onCallback,
  }) async {
    final initial = await _appLinks.getInitialLink();
    if (initial != null) {
      await onCallback(initial);
    }

    await _linkSubscription?.cancel();
    _linkSubscription = _appLinks.uriLinkStream.listen((uri) {
      onCallback(uri);
    });
  }

  Future<void> dispose() async {
    await _linkSubscription?.cancel();
    _client.close();
  }

  Future<void> connect() async {
    final loginUri = Uri.parse('$_baseUrl/auth/pollinations/login').replace(
      queryParameters: const {
        'client': 'mobile',
        'return_to': _returnTo,
      },
    );

    final opened = await launchUrl(
      loginUri,
      mode: LaunchMode.externalApplication,
    );
    if (!opened) {
      throw const PollinationsSessionException(
        'Could not open the Pollinations authorization page.',
      );
    }
  }

  bool isPollinationsCallback(Uri uri) {
    return uri.scheme == 'soloforge' &&
        uri.host == 'oauth' &&
        uri.path == '/pollinations';
  }

  Future<PollinationsSessionState> handleCallback(Uri uri) async {
    if (!isPollinationsCallback(uri)) {
      throw const PollinationsSessionException('Unexpected OAuth callback URL.');
    }

    final code = uri.queryParameters['code'];
    if (code == null || code.isEmpty) {
      throw const PollinationsSessionException(
        'Pollinations authorization did not return a handoff code.',
      );
    }

    final exchangeUri = Uri.parse('$_baseUrl/auth/pollinations/mobile/exchange');
    final response = await _client.post(
      exchangeUri,
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'code': code}),
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw PollinationsSessionException(_errorMessage(response));
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final sessionToken = body['session_token']?.toString();
    if (sessionToken == null || sessionToken.isEmpty) {
      throw const PollinationsSessionException(
        'SoloForge did not receive a Pollinations session token.',
      );
    }

    await _storage.write(key: _sessionKey, value: sessionToken);
    return PollinationsSessionState(
      connected: true,
      expiresAt: _asInt(body['expires_at']),
      scope: body['scope']?.toString(),
    );
  }

  Future<PollinationsSessionState> status() async {
    final token = await readSessionToken();
    if (token == null || token.isEmpty) {
      return const PollinationsSessionState(connected: false);
    }

    final response = await _client.get(
      Uri.parse('$_baseUrl/auth/pollinations/status'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      await _storage.delete(key: _sessionKey);
      return const PollinationsSessionState(connected: false);
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final connected = body['connected'] == true;
    if (!connected) {
      await _storage.delete(key: _sessionKey);
    }
    return PollinationsSessionState(
      connected: connected,
      expiresAt: _asInt(body['expires_at']),
      scope: body['scope']?.toString(),
    );
  }

  Future<void> disconnect() async {
    final token = await readSessionToken();
    try {
      if (token != null && token.isNotEmpty) {
        await _client.post(
          Uri.parse('$_baseUrl/auth/pollinations/logout'),
          headers: {'Authorization': 'Bearer $token'},
        );
      }
    } finally {
      await _storage.delete(key: _sessionKey);
    }
  }

  Future<Map<String, String>> authorizationHeaders() async {
    final token = await readSessionToken();
    if (token == null || token.isEmpty) {
      throw const PollinationsSessionException(
        'Connect Pollinations before generating assets.',
      );
    }
    return {'Authorization': 'Bearer $token'};
  }

  int? _asInt(Object? value) {
    if (value is int) return value;
    return int.tryParse(value?.toString() ?? '');
  }

  String _errorMessage(http.Response response) {
    try {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      return body['detail']?.toString() ??
          'Pollinations connection failed (${response.statusCode}).';
    } catch (_) {
      return 'Pollinations connection failed (${response.statusCode}).';
    }
  }
}

class PollinationsSessionException implements Exception {
  const PollinationsSessionException(this.message);

  final String message;

  @override
  String toString() => message;
}

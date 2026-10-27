import 'dart:async';
import 'dart:convert';

import 'soloforge_session_service.dart';

import 'package:app_links/app_links.dart';
import 'package:flutter/foundation.dart';
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
    Future<Map<String, String>> Function()? ownerAuthorization,
  }) : _client = client ?? http.Client(),
       _storage = storage ?? const FlutterSecureStorage(),
       _appLinks = appLinks ?? AppLinks(),
       _ownerAuthorization = ownerAuthorization,
       _ownerSessions = ownerAuthorization == null
           ? SoloForgeSessionService(useOwnerV2: true)
           : null;

  static const _sessionKey = 'pollinations_session_token';
  static const _returnTo = 'soloforge://oauth/pollinations';

  // Image Generation and Prawtwan use the same storage and OAuth transaction.
  // These coordinate instances; they never grant execution/spending permission.
  static Future<void>? _connecting;
  static final Map<String, Future<PollinationsSessionState>> _exchanges = {};
  static final Set<String> _completedExchanges = {};
  static Future<void> _storageUpdates = Future.value();

  Future<void> _updateStorage(Future<void> Function() action) async {
    final update = _storageUpdates.then((_) => action());
    _storageUpdates = update.then<void>((_) {}, onError: (Object _) {});
    await update;
  }

  final http.Client _client;
  final FlutterSecureStorage _storage;
  final AppLinks _appLinks;
  final Future<Map<String, String>> Function()? _ownerAuthorization;
  final SoloForgeSessionService? _ownerSessions;

  Future<Map<String, String>> _ownerHeaders() =>
      _ownerAuthorization?.call() ?? _ownerSessions!.authorizationHeaders();
  StreamSubscription<Uri>? _linkSubscription;

  String get _baseUrl =>
      assetForgeApiUrl.trim().replaceFirst(RegExp(r'/$'), '');

  Future<String?> readSessionToken() => _storage.read(key: _sessionKey);

  // BYOP keeps opaque record IDs per application principal. Provider secrets
  // are sent once to the backend and are never persisted by this service.
  Future<String?> byopCredentialId(String principal) =>
      _storage.read(key: 'pollinations_byop_id_$principal');

  Future<Map<String, String>> _byopHeaders(String principal) async {
    final headers = await _ownerHeaders();
    final response = await _client.get(
      Uri.parse('$_baseUrl/v1/byop/session'), headers: headers,
    ).timeout(const Duration(seconds: 20));
    if (response.statusCode != 200 ||
        (jsonDecode(response.body) as Map<String, dynamic>)['principal'] != principal) {
      throw const PollinationsSessionException('Active application principal changed or is unavailable.');
    }
    if ((await _ownerHeaders())['Authorization'] != headers['Authorization']) {
      throw const PollinationsSessionException('Account changed during BYOP validation.');
    }
    return headers;
  }

  Future<Map<String, dynamic>> _byopResult(http.Response response) async {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw PollinationsSessionException(_errorMessage(response));
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> submitByopKey(String principal, String key) async {
    final headers = await _byopHeaders(principal);
    final result = await _byopResult(await _client.post(
      Uri.parse('$_baseUrl/v1/byop/credentials'),
      headers: {...headers, 'Content-Type': 'application/json'},
      body: jsonEncode({'access_token': key}),
    ).timeout(const Duration(seconds: 30)));
    await _byopHeaders(principal);
    final id = result['credential_id'] as String;
    await _updateStorage(() => _storage.write(key: 'pollinations_byop_id_$principal', value: id));
    return result;
  }

  Future<Map<String, dynamic>> byopStatus(String principal) async {
    final headers = await _byopHeaders(principal);
    final id = await byopCredentialId(principal);
    if (id == null) return {'connected': false, 'spending_authorized': false};
    return _byopResult(await _client.get(
      Uri.parse('$_baseUrl/v1/byop/credentials/$id'), headers: headers,
    ).timeout(const Duration(seconds: 20)));
  }

  Future<void> selectByopCredential(String principal, String id) async {
    final headers = await _byopHeaders(principal);
    final result = await _byopResult(await _client.get(
      Uri.parse('$_baseUrl/v1/byop/credentials/$id'), headers: headers,
    ).timeout(const Duration(seconds: 20)));
    if (result['credential_id'] != id || result['connected'] != true) {
      throw const PollinationsSessionException('Select an active credential belonging to this account.');
    }
    await _byopHeaders(principal);
    await _updateStorage(() => _storage.write(key: 'pollinations_byop_id_$principal', value: id));
  }

  Future<Map<String, dynamic>> verifyByopCredential(String principal) async {
    final headers = await _byopHeaders(principal);
    final id = await byopCredentialId(principal);
    if (id == null) throw const PollinationsSessionException('Connect your own credential first.');
    return _byopResult(await _client.post(
      Uri.parse('$_baseUrl/v1/byop/credentials/$id/verify'), headers: headers,
    ).timeout(const Duration(seconds: 30)));
  }

  Future<void> disconnectByop(String principal) async {
    final headers = await _byopHeaders(principal);
    final id = await byopCredentialId(principal);
    if (id == null) return;
    final result = await _byopResult(await _client.post(
      Uri.parse('$_baseUrl/v1/byop/credentials/$id/disconnect'), headers: headers,
    ).timeout(const Duration(seconds: 20)));
    if (result['server_revocation_confirmed'] != true) {
      throw const PollinationsSessionException('Server disconnect is unconfirmed.');
    }
    await _updateStorage(() => _storage.delete(key: 'pollinations_byop_id_$principal'));
  }

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
    _ownerSessions?.dispose();
  }

  Future<void> connect() {
    return _connecting ??= _connectOnce().whenComplete(
      () => _connecting = null,
    );
  }

  Future<void> _connectOnce() async {
    final existingSession = await status();
    if (existingSession.connected) {
      return;
    }

    final queryParameters = <String, String>{};
    LaunchMode mode = LaunchMode.externalApplication;
    String? webOnlyWindowName;

    if (kIsWeb) {
      queryParameters['client'] = 'web';
      queryParameters['return_to'] = '${Uri.base.origin}/';
      mode = LaunchMode.platformDefault;
      webOnlyWindowName = '_self';
    } else {
      queryParameters['client'] = 'mobile';
      queryParameters['return_to'] = _returnTo;
    }

    final ownerHeaders = await _ownerHeaders();
    final response = await _client.post(
      Uri.parse('$_baseUrl/auth/pollinations/connect'),
      headers: {...ownerHeaders, 'Content-Type': 'application/json'},
      body: jsonEncode(queryParameters),
    );
    if (response.statusCode != 200) {
      throw PollinationsSessionException(_errorMessage(response));
    }
    final path =
        (jsonDecode(response.body) as Map<String, dynamic>)['launch_path']
            as String;
    if (!path.startsWith('/auth/pollinations/launch?ticket=')) {
      throw const PollinationsSessionException('Invalid connection response.');
    }
    final loginUri = Uri.parse('$_baseUrl$path');

    final opened = await launchUrl(
      loginUri,
      mode: mode,
      webOnlyWindowName: webOnlyWindowName,
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
      throw const PollinationsSessionException(
        'Unexpected OAuth callback URL.',
      );
    }

    final code = uri.queryParameters['code'];
    if (code == null || code.isEmpty) {
      throw const PollinationsSessionException(
        'Pollinations authorization did not return a handoff code.',
      );
    }
    return restoreCallbackCode(code);
  }

  Future<PollinationsSessionState> handleWebCallbackIfPresent() async {
    if (!kIsWeb) {
      return status();
    }

    return restoreCallbackCode(Uri.base.queryParameters['code']);
  }

  // Also used by native callbacks. Validate the saved token, not its presence.
  Future<PollinationsSessionState> restoreCallbackCode(String? code) async {
    final existing = await status();
    if (existing.connected || code == null || code.isEmpty) return existing;
    final key = '$_baseUrl:$code';
    final exchange = _exchanges[key];
    if (exchange != null) {
      // Concurrent listeners share a single exchange. A completed code must
      // never restore a revoked/expired session from a cached success.
      await exchange;
      return status();
    }
    if (_completedExchanges.contains(key)) return existing;
    final pending = _exchangeHandoffCode(code).whenComplete(() {
      _exchanges.remove(key);
      _completedExchanges.add(key);
      // Bound completed-code retention; never evict an in-flight exchange.
      if (_completedExchanges.length > 16) {
        _completedExchanges.remove(_completedExchanges.first);
      }
    });
    _exchanges[key] = pending;
    return pending;
  }

  Future<PollinationsSessionState> _exchangeHandoffCode(String code) async {
    final exchangeUri = Uri.parse(
      '$_baseUrl/auth/pollinations/mobile/exchange',
    );
    final response = await _client.post(
      exchangeUri,
      headers: {...await _ownerHeaders(), 'Content-Type': 'application/json'},
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

    await _updateStorage(
      () => _storage.write(key: _sessionKey, value: sessionToken),
    );
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
      headers: {...await _ownerHeaders(), 'X-Pollinations-Session': token},
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      // A transient backend outage is not evidence that OAuth was revoked.
      if (response.statusCode != 401 &&
          response.statusCode != 403 &&
          response.statusCode != 404) {
        throw PollinationsSessionException(_errorMessage(response));
      }
      await _invalidateToken(token);
      if (await readSessionToken() != null) return status();
      return const PollinationsSessionState(connected: false);
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final connected = body['connected'] == true;
    if (!connected) {
      await _invalidateToken(token);
    }
    if (await readSessionToken() != (connected ? token : null)) return status();
    return PollinationsSessionState(
      connected: connected,
      expiresAt: _asInt(body['expires_at']),
      scope: body['scope']?.toString(),
    );
  }

  Future<void> _invalidateToken(String token) => _updateStorage(() async {
    if (await readSessionToken() == token) {
      await _storage.delete(key: _sessionKey);
    }
  });

  Future<void> disconnect() async {
    final token = await readSessionToken();
    try {
      if (token != null && token.isNotEmpty) {
        await _client.post(
          Uri.parse('$_baseUrl/auth/pollinations/logout'),
          headers: {...await _ownerHeaders(), 'X-Pollinations-Session': token},
        );
      }
    } finally {
      if (token != null) await _invalidateToken(token);
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

  Future<Map<String, String>> optionalAuthorizationHeaders() async {
    final token = await readSessionToken();
    if (token == null || token.isEmpty) {
      return const <String, String>{};
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

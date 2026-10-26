import 'dart:async';

import 'package:flutter/material.dart';

import 'core/theme/app_theme.dart';
import 'pages/home_page.dart';
import 'pages/owner_v2_login_page.dart';
import 'services/owner_v2_session_service.dart';
import 'pages/owner_oauth_uat_page.dart';
import 'services/soloforge_session_service.dart';

import 'package:supabase_flutter/supabase_flutter.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (!ownerV2Enabled ||
      const bool.fromEnvironment('SOLOFORGE_OWNER_OAUTH_UAT')) {
    await Supabase.initialize(
      url: const String.fromEnvironment(
        'SUPABASE_URL',
        defaultValue: 'https://dhazxwfzaccrttckuylw.supabase.co',
      ),
      publishableKey: const String.fromEnvironment(
        'SUPABASE_PUBLISHABLE_KEY',
        defaultValue: 'sb_publishable_3_UQoHsxK1k8_umfgdTHBA_s5nhhKoL',
      ),
    );
  }
  runApp(const SoloForgeApp());
}

class SoloForgeApp extends StatelessWidget {
  const SoloForgeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'SoloForge AI',
      theme: SoloForgeTheme.dark(),
      home: const bool.fromEnvironment('SOLOFORGE_OWNER_OAUTH_UAT')
          ? const OwnerOAuthUatPage()
          : ownerV2Enabled
          ? const OwnerV2AppGate()
          : const OwnerAppGate(),
    );
  }
}

class OwnerAppGate extends StatefulWidget {
  const OwnerAppGate({super.key});

  @override
  State<OwnerAppGate> createState() => _OwnerAppGateState();
}

class _OwnerAppGateState extends State<OwnerAppGate> {
  final SoloForgeSessionService _sessions = SoloForgeSessionService();
  StreamSubscription<AuthState>? _subscription;
  bool _authorized = false;
  bool _checking = true;
  String? _ownerError;
  int _checkGeneration = 0;

  @override
  void initState() {
    super.initState();
    _subscription = Supabase.instance.client.auth.onAuthStateChange.listen((_) {
      _checkOwner();
    });
    _checkOwner();
  }

  Future<void> _checkOwner() async {
    if (!mounted) return;
    final generation = ++_checkGeneration;
    final userId = Supabase.instance.client.auth.currentUser?.id;
    if (userId == null ||
        Supabase.instance.client.auth.currentSession == null) {
      await _sessions.clear();
      if (mounted && generation == _checkGeneration) {
        setState(() {
          _checking = false;
          _authorized = false;
        });
      }
      return;
    }
    setState(() {
      _checking = true;
      _authorized = false;
    });
    var authorized = false;
    String? error;
    try {
      await _sessions.authorizationHeaders();
      authorized =
          Supabase.instance.client.auth.currentUser?.id == userId &&
          Supabase.instance.client.auth.currentSession != null;
    } on SoloForgeSessionException catch (exc) {
      error = exc.message;
    } catch (_) {
      error = 'Cannot connect to SoloForge. Please retry.';
    }
    if (mounted && generation == _checkGeneration) {
      setState(() {
        _checking = false;
        _authorized = authorized;
        _ownerError = error;
      });
    }
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _sessions.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return _authorized
        ? const HomePage()
        : OwnerOAuthUatPage(
            identityOnly: false,
            onRetry: _checkOwner,
            ownerAccessMessage: _ownerError,
          );
  }
}

/// Opt-in V2 UI; the legacy gate remains available in default builds.
class OwnerV2AppGate extends StatefulWidget {
  const OwnerV2AppGate({super.key});
  @override
  State<OwnerV2AppGate> createState() => _OwnerV2AppGateState();
}

class _OwnerV2AppGateState extends State<OwnerV2AppGate>
    with WidgetsBindingObserver {
  final _sessions = OwnerV2SessionService.shared;
  bool _loggingOut = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _sessions.addListener(_changed);
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _sessions.authenticated) {
      _validate();
    }
  }

  Future<void> _validate() async {
    try {
      await _sessions.authorizationHeaders();
    } catch (_) {
      // The session service clears access on failed validation.
    }
  }

  Future<void> _logout() async {
    setState(() {
      _loggingOut = true;
    });
    try {
      await _sessions.logout();
    } on OwnerV2Exception {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Signed out locally. Server revocation could not be confirmed; the session will expire.',
            ),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _loggingOut = false;
        });
      }
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _sessions.removeListener(_changed);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_sessions.authenticated) return OwnerV2LoginPage(sessions: _sessions);
    return Material(
      child: Column(
        children: [
          SafeArea(
            bottom: false,
            child: Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: _loggingOut ? null : _logout,
                child: const Text('Sign out'),
              ),
            ),
          ),
          const Expanded(child: HomePage()),
        ],
      ),
    );
  }
}

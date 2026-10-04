import 'dart:async';

import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';
import 'pages/home_page.dart';
import 'pages/owner_oauth_uat_page.dart';
import 'services/soloforge_session_service.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Supabase.initialize(
    url: const String.fromEnvironment('SUPABASE_URL',
        defaultValue: 'https://dhazxwfzaccrttckuylw.supabase.co'),
    publishableKey: const String.fromEnvironment('SUPABASE_PUBLISHABLE_KEY',
        defaultValue: 'sb_publishable_3_UQoHsxK1k8_umfgdTHBA_s5nhhKoL'),
  );
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
    if (Supabase.instance.client.auth.currentSession == null) {
      await _sessions.clear();
      if (mounted) setState(() { _checking = false; _authorized = false; });
      return;
    }
    setState(() { _checking = true; _authorized = false; });
    var authorized = false;
    try {
      await _sessions.authorizationHeaders();
      authorized = Supabase.instance.client.auth.currentSession != null;
    } catch (_) {
      authorized = false;
    }
    if (mounted) setState(() { _checking = false; _authorized = authorized; });
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
    return _authorized ? const HomePage() : const OwnerOAuthUatPage();
  }
}

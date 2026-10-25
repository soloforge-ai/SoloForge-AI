import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'core/theme/app_theme.dart';
import 'pages/home_page.dart';
import 'pages/owner_v2_login_page.dart';
import 'services/owner_v2_session_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Other app features still depend on the Supabase client for data access.
  // This does not authenticate the owner or authorize API calls.
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
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'SoloForge AI',
    theme: SoloForgeTheme.dark(),
    home: const OwnerAppGate(),
  );
}

class OwnerAppGate extends StatefulWidget {
  const OwnerAppGate({super.key});
  @override
  State<OwnerAppGate> createState() => _OwnerAppGateState();
}

class _OwnerAppGateState extends State<OwnerAppGate> {
  final OwnerV2SessionService _session = OwnerV2SessionService.shared;
  bool _authenticated = false;

  @override
  Widget build(BuildContext context) => _authenticated
      ? Scaffold(
          body: const HomePage(),
          floatingActionButton: FloatingActionButton.extended(
            onPressed: () async {
              try {
                await _session.logout();
              } catch (_) {
                // Local session was already cleared; never keep owner access open.
              }
              if (mounted) setState(() => _authenticated = false);
            },
            icon: const Icon(Icons.logout),
            label: const Text('Owner logout'),
          ),
        )
      : OwnerV2LoginPage(
          session: _session,
          onAuthenticated: () {
            if (mounted) setState(() => _authenticated = true);
          },
        );
}

import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';
import 'pages/home_page.dart';
import 'pages/owner_oauth_uat_page.dart';
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
          : const HomePage(),
    );
  }
}

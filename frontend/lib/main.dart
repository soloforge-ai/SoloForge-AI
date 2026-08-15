import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';
import 'pages/home_page.dart';

void main() {
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
      home: const HomePage(),
    );
  }
}

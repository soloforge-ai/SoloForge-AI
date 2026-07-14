import 'package:flutter/material.dart';
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
      theme: ThemeData.dark(),
      home: const HomePage(),
    );
  }
}
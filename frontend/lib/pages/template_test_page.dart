import 'package:flutter/material.dart';

import '../ai/template_engine.dart';

class TemplateTestPage extends StatefulWidget {
  const TemplateTestPage({super.key});

  @override
  State<TemplateTestPage> createState() => _TemplateTestPageState();
}

class _TemplateTestPageState extends State<TemplateTestPage> {
  String result = 'Loading...';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final template = await const TemplateEngine().loadTemplate(
      platform: 'tiktok',
      template: 'cute_toy',
    );

    setState(() {
      result = template.toString();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Template Test')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: SelectableText(result),
      ),
    );
  }
}

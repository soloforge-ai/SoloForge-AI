import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../services/pollinations_image_service.dart';

class PollinationsTestPage extends StatefulWidget {
  const PollinationsTestPage({super.key});

  @override
  State<PollinationsTestPage> createState() => _PollinationsTestPageState();
}

class _PollinationsTestPageState extends State<PollinationsTestPage> {
  final _apiKeyController = TextEditingController();
  final _promptController = TextEditingController(
    text: 'Cute 3D chibi celestial baby fairy, Pearli, soft pastel colors, clean character art',
  );
  final _service = const PollinationsImageService();

  String _model = 'flux';
  Uint8List? _image;
  String _status = 'Ready to test Pollinations.';
  bool _loading = false;

  @override
  void dispose() {
    _apiKeyController.dispose();
    _promptController.dispose();
    super.dispose();
  }

  Future<void> _generate() async {
    final key = _apiKeyController.text.trim();
    final prompt = _promptController.text.trim();

    if (key.isEmpty) {
      setState(() => _status = 'กรุณาใส่ Pollinations API key ก่อน');
      return;
    }
    if (prompt.isEmpty) {
      setState(() => _status = 'กรุณาใส่ Prompt ก่อน');
      return;
    }

    setState(() {
      _loading = true;
      _image = null;
      _status = 'กำลังส่งคำขอไป Pollinations...';
    });

    try {
      final bytes = await _service.generateImage(
        prompt: prompt,
        apiKey: key,
        model: _model,
        width: 768,
        height: 768,
      );

      if (!mounted) return;
      setState(() {
        _image = bytes;
        _status = 'เชื่อมต่อสำเร็จ — ได้ภาพกลับมาแล้ว';
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _status = 'เชื่อมต่อไม่สำเร็จ: $error';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pollinations Test')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  'ขั้นนี้ใช้ทดสอบการเชื่อมต่อจริงเท่านั้น\n\n'
                  'API key จะอยู่ในหน่วยความจำของแอปและไม่ได้ถูกบันทึกลง GitHub.',
                ),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _apiKeyController,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Pollinations API key',
                hintText: 'sk_...',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _model,
              decoration: const InputDecoration(
                labelText: 'Image model',
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(value: 'flux', child: Text('Flux — test')),
                DropdownMenuItem(value: 'zimage', child: Text('ZImage')),
                DropdownMenuItem(value: 'gptimage', child: Text('GPT Image')),
                DropdownMenuItem(value: 'nanobanana', child: Text('NanoBanana')),
              ],
              onChanged: _loading ? null : (value) {
                if (value != null) setState(() => _model = value);
              },
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _promptController,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Prompt',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 20),
            SizedBox(
              height: 52,
              child: ElevatedButton.icon(
                onPressed: _loading ? null : _generate,
                icon: Icon(_loading ? Icons.hourglass_top : Icons.auto_awesome),
                label: Text(_loading ? 'Generating...' : 'TEST GENERATE IMAGE'),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              _status,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: _image != null
                    ? Theme.of(context).colorScheme.primary
                    : null,
              ),
            ),
            if (_image != null) ...[
              const SizedBox(height: 16),
              ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Image.memory(_image!, fit: BoxFit.contain),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

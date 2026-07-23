import 'package:flutter/material.dart';

import '../character/services/character_engine.dart';
import '../creative/services/creative_engine.dart';
import '../scene/services/scene_engine.dart';

import '../image/models/generated_image.dart';
import '../image/services/image_engine.dart';


class ImageTestPage extends StatefulWidget {
  const ImageTestPage({
    super.key,
  });

  @override
  State<ImageTestPage> createState() =>
      _ImageTestPageState();
}

class _ImageTestPageState
    extends State<ImageTestPage> {
  bool _loading = true;
  bool _generating = false;

  GeneratedImage? _image;

  String? _error;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
  try {
    await CharacterEngine.initialize();
    await CreativeEngine.initialize();
    await SceneEngine.initialize();

    if (!mounted) return;

    setState(() {
      _loading = false;
    });
  } catch (e, stack) {
    debugPrint('========== ERROR ==========');
    debugPrint(e.toString());
    debugPrint(stack.toString());

    if (!mounted) return;

    setState(() {
      _loading = false;
      _error = e.toString();
    });
  }
}

  Future<void> _generateImage() async {
    setState(() {
      _generating = true;
    });

    try {
      final image =
          await ImageEngine.generate(
        character: CharacterEngine.current,
        creative: CreativeEngine.current,
        scene: SceneEngine.current,
        product: {
          "id": "demo",
          "name": "Demo Product",
          "description":
              "SoloForge AI Test Product",
        },
      );

      if (!mounted) return;

      setState(() {
        _image = image;
      });
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context)
          .showSnackBar(
        SnackBar(
          content: Text(
            e.toString(),
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _generating = false;
        });
      }
    }
  }

  Widget _buildResult() {
    if (_image == null) {
      return const Text(
        "Press Generate Image",
      );
    }

    return Column(
      crossAxisAlignment:
          CrossAxisAlignment.start,
      children: [
        const Text(
          "Provider",
          style: TextStyle(
            fontWeight: FontWeight.bold,
          ),
        ),

        Text(_image!.provider),

        const SizedBox(height: 20),

        const Text(
          "Prompt",
          style: TextStyle(
            fontWeight: FontWeight.bold,
          ),
        ),

        SelectableText(
          _image!.prompt,
        ),

        const SizedBox(height: 20),

        const Text(
          "Image URL",
          style: TextStyle(
            fontWeight: FontWeight.bold,
          ),
        ),

        SelectableText(
          _image!.url,
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        body: Center(
          child:
              CircularProgressIndicator(),
        ),
      );
    }

    if (_error != null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text(
            "Image Test",
          ),
        ),
        body: Center(
          child: Text(_error!),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "Image Engine Test",
        ),
      ),
      body: SingleChildScrollView(
        padding:
            const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _generating
                    ? null
                    : _generateImage,
                child: const Text(
                  "Generate Image",
                ),
              ),
            ),

            if (_generating)
              const Padding(
                padding:
                    EdgeInsets.only(
                  top: 16,
                ),
                child:
                    LinearProgressIndicator(),
              ),

            const SizedBox(height: 30),

            _buildResult(),
          ],
        ),
      ),
    );
  }
}
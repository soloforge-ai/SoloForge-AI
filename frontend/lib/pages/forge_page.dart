import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/affiliate_product.dart';

import '../widgets/forge/product_header.dart';
import '../widgets/forge/miniboss_card.dart';
import '../widgets/forge/analysis_card.dart';
import '../widgets/forge/content_studio.dart';
import '../engine/generate_engine.dart';

class ForgePage extends StatefulWidget {
  final AffiliateProduct product;

  const ForgePage({
    super.key,
    required this.product,
  });

  @override
  State<ForgePage> createState() => _ForgePageState();
}

class _ForgePageState extends State<ForgePage> {
    int selectedPlatform = 0;

final captionController = TextEditingController();

final hookController = TextEditingController();

final hashtagController = TextEditingController();

final ctaController = TextEditingController();

final platforms = const [
  "Facebook",
  "TikTok",
  "Lemon8",
  "Threads",
  "YouTube",
];

final generateEngine = const GenerateEngine();

void generateContent() {
  final content = generateEngine.generate(widget.product);

  setState(() {
    hookController.text = content.hook;
    captionController.text = content.caption;
    hashtagController.text = content.hashtags.join(" ");
    ctaController.text = content.callToAction;
  });
}



@override
void dispose() {
  captionController.dispose();
  hookController.dispose();
  hashtagController.dispose();
  ctaController.dispose();
  super.dispose();
}

void copyToClipboard(String text) {
  Clipboard.setData(ClipboardData(text: text));

  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(
      content: Text("Copied"),
      duration: Duration(seconds: 1),
    ),
  );
}


  @override
  Widget build(BuildContext context) {
  final product = widget.product; 
    return Scaffold(
      appBar: AppBar(
        title: const Text("AI Forge"),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ProductHeader(product: product),

            const SizedBox(height: 20),


            MiniBossCard(product: product),

            const SizedBox(height: 20),


            const AnalysisCard(),

            const SizedBox(height: 24),

ContentStudio(
  selectedPlatform: selectedPlatform,
  platforms: platforms,

  hookController: hookController,
  captionController: captionController,
  hashtagController: hashtagController,
  ctaController: ctaController,

  onPlatformChanged: (index) {
    setState(() {
      selectedPlatform = index;
    });
  },

  onCopy: () {
    copyToClipboard(
      '''
${hookController.text}

${captionController.text}

${hashtagController.text}

${ctaController.text}
''',
    );
  },
),

const SizedBox(height: 24),

TextField(
  controller: captionController,
  maxLines: 4,
  decoration: const InputDecoration(
    labelText: "Caption",
    border: OutlineInputBorder(),
    hintText: "AI จะสร้าง Caption ที่นี่",
  ),
),

const SizedBox(height: 12),

SizedBox(
  width: double.infinity,
  child: FilledButton.icon(
    onPressed: () {
      copyToClipboard(captionController.text);
    },
    icon: const Icon(Icons.copy),
    label: const Text("Copy Caption"),
  ),
),


],
    ),
  ),
    );

const SizedBox(height: 24);
 
  }
}
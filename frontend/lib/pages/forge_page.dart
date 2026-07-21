import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/affiliate_product.dart';

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
            Text(
              product.title,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 12),

            Text("🏪 ${product.shopName}"),

            const SizedBox(height: 8),

            Text("💰 ${product.priceText}"),

            Text("🛒 ${product.soldText}"),

            Text(
              "💸 ${product.commissionAmountText} (${product.commissionRateText})",
            ),

            const SizedBox(height: 20),

            Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "MiniBoss Score",
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    SizedBox(height: 10),
                    LinearProgressIndicator(
                      value: product.miniBossScore / 10,
                    ),
                    SizedBox(height: 8),
                    Text(
                      product.miniBossScore.toStringAsFixed(1),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 20),

            Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text(
                      "AI Analysis",
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                      ),
                    ),
                    SizedBox(height: 12),
                    Text("• จุดเด่นของสินค้า"),
                    Text("• เหมาะกับใคร"),
                    Text("• Hook สำหรับคลิป"),
                    Text("• ไอเดียรีวิว"),
                    Text("• CTA"),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),

SizedBox(
  width: double.infinity,
  child: Card(
    child: Padding(
    padding: const EdgeInsets.all(16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          "Content Studio",
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
   
),

        const SizedBox(height: 16),

        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: List.generate(
            platforms.length,
            (index) {
              return ChoiceChip(
                label: Text(platforms[index]),
                selected: selectedPlatform == index,
                onSelected: (value) {
                  setState(() {
                    selectedPlatform = index;
                  });
                },
              );
            },
          ),
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
    ),
    ),

const SizedBox(height: 24),
          
   ],
   ),
      ),
    );
  }
}
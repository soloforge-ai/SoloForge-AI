import 'package:flutter/material.dart';

class AnalysisCard extends StatelessWidget {
  const AnalysisCard({
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text(
              "AI Analysis",
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
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
    );
  }
}
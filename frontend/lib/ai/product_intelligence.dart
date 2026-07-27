import '../models/product.dart';

class ProductIntelligence {
  final String category;
  final List<String> keywords;
  final List<String> audience;
  final List<String> sellingPoints;
  final List<String> painPoints;

  const ProductIntelligence({
    required this.category,
    required this.keywords,
    required this.audience,
    required this.sellingPoints,
    required this.painPoints,
  });
}

class ProductIntelligenceEngine {
  const ProductIntelligenceEngine();

  ProductIntelligence analyze(Product product) {
    final title = product.name.toLowerCase();

    String category = "General";

    final keywords = <String>[];
    final audience = <String>[];
    final sellingPoints = <String>[];
    final painPoints = <String>[];

    //----------------------------------------------------
    // Cute Collection
    //----------------------------------------------------

    if (title.contains("squishy") ||
        title.contains("สกุชชี่") ||
        title.contains("cheese") ||
        title.contains("ชีส") ||
        title.contains("bread") ||
        title.contains("ขนมปัง") ||
        title.contains("toast") ||
        title.contains("capybara") ||
        title.contains("เป็ด") ||
        title.contains("duck") ||
        title.contains("cat") ||
        title.contains("แมว") ||
        title.contains("rabbit") ||
        title.contains("กระต่าย")) {
      category = "Cute Toy";

      keywords.addAll(["Cute", "Squishy", "Soft"]);

      audience.addAll(["นักเรียน", "วัยรุ่น", "วัยทำงาน", "คนชอบของน่ารัก"]);

      sellingPoints.addAll([
        "นุ่มเด้ง",
        "บีบเพลิน",
        "คลายเครียด",
        "ตกแต่งโต๊ะทำงาน",
        "เหมาะเป็นของขวัญ",
      ]);

      painPoints.addAll([
        "เครียดจากการทำงาน",
        "อยากหาของน่ารัก",
        "โต๊ะทำงานดูน่าเบื่อ",
      ]);
    }

    //----------------------------------------------------
    // Squishy
    //----------------------------------------------------

    if (title.contains("squishy") || title.contains("สกุชชี่")) {
      keywords.add("Stress Relief");

      sellingPoints.addAll(["สัมผัสนุ่ม", "คืนตัวช้า"]);

      painPoints.addAll(["ชอบของเล่นคลายเครียด"]);
    }

    //----------------------------------------------------
    // Cheese
    //----------------------------------------------------

    if (title.contains("cheese") || title.contains("ชีส")) {
      keywords.add("Cheese");

      sellingPoints.addAll(["ดีไซน์ชีสน่ารัก", "เหมาะสะสม"]);
    }

    //----------------------------------------------------
    // Bread
    //----------------------------------------------------

    if (title.contains("bread") ||
        title.contains("ขนมปัง") ||
        title.contains("toast")) {
      keywords.add("Bread");

      sellingPoints.addAll(["ดีไซน์เหมือนขนมจริง"]);
    }

    return ProductIntelligence(
      category: category,
      keywords: keywords.toSet().toList(),
      audience: audience.toSet().toList(),
      sellingPoints: sellingPoints.toSet().toList(),
      painPoints: painPoints.toSet().toList(),
    );
  }
}

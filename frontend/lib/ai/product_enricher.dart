import '../models/product.dart';

class ProductEnricher {
  const ProductEnricher();

  Product enrich(Product product) {
    final name = product.name.toLowerCase();

    final tags = <String>[...product.tags];
    final keywords = <String>[...product.keywords];

    String? description = product.description;
    String? mood = product.mood;
    String? targetAudience = product.targetAudience;

    bool suitableForShortVideo = product.suitableForShortVideo;
    bool ceoApproved = product.ceoApproved;

    // =====================================================
    // Cute Collection
    // =====================================================

    if (_containsAny(name, [
      'squishy',
      'สกุชชี่',
      'cheese',
      'ชีส',
      'bread',
      'toast',
      'ขนมปัง',
      'capybara',
      'เป็ด',
      'duck',
      'cat',
      'แมว',
      'rabbit',
      'กระต่าย',
    ])) {
      _addAll(tags, [
        'Cute',
        'Desk Toy',
        'Stress Relief',
      ]);

      _addAll(keywords, [
        'Cute',
        'Soft',
        'Squishy',
      ]);

      description ??=
          'ของเล่นสกุชชี่สุดนุ่ม บีบเพลิน ช่วยคลายเครียด เหมาะสำหรับตั้งโต๊ะทำงานหรือสะสม';

      mood ??= 'Cute';

      targetAudience ??=
          'นักเรียน วัยทำงาน และคนชอบของน่ารัก';

      suitableForShortVideo = true;
    }

    // =====================================================
    // Cheese
    // =====================================================

    if (_containsAny(name, [
      'cheese',
      'ชีส',
    ])) {
      _addAll(tags, [
        'Cheese',
      ]);

      _addAll(keywords, [
        'Cheese',
      ]);

      description ??=
          'สกุชชี่ชีสดีไซน์น่ารัก เนื้อนุ่ม คืนตัวช้า บีบเพลิน';

      ceoApproved = true;
    }

    // =====================================================
    // Bread
    // =====================================================

    if (_containsAny(name, [
      'bread',
      'toast',
      'ขนมปัง',
    ])) {
      _addAll(tags, [
        'Bread',
      ]);

      _addAll(keywords, [
        'Bread',
      ]);

      description ??=
          'สกุชชี่ขนมปังเนื้อนุ่ม ดีไซน์เหมือนของจริง';

      suitableForShortVideo = true;
    }

    // =====================================================
    // Capybara
    // =====================================================

    if (_containsAny(name, [
      'capybara',
    ])) {
      _addAll(tags, [
        'Capybara',
      ]);

      _addAll(keywords, [
        'Capybara',
      ]);

      mood = 'Healing';

      description ??=
          'ของสะสมสุดน่ารักสำหรับคนรักคาปิบารา';

      suitableForShortVideo = true;
    }

    return product.copyWith(
      description: description,
      tags: tags.toSet().toList(),
      keywords: keywords.toSet().toList(),
      mood: mood,
      targetAudience: targetAudience,
      suitableForShortVideo: suitableForShortVideo,
      ceoApproved: ceoApproved,
    );
  }

  bool _containsAny(String text, List<String> values) {
    return values.any(text.contains);
  }

  void _addAll(List<String> target, List<String> values) {
    for (final value in values) {
      if (!target.contains(value)) {
        target.add(value);
      }
    }
  }
}
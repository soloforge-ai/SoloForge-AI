import '../../models/generated_content.dart';
import '../platforms.dart';
import 'ai_provider.dart';

class MockProvider implements AIProvider {
  const MockProvider();

  @override
  Future<GeneratedContent> generateContent({
    required String prompt,
    required PlatformType platform,
  }) async {
    await Future.delayed(
      const Duration(seconds: 1),
    );

    final lower = prompt.toLowerCase();

    String title;
    String hook;
    String caption;
    List<String> hashtags;

    if (lower.contains('squishy') ||
        lower.contains('สกุชชี่') ||
        lower.contains('cheese') ||
        lower.contains('ชีส')) {
      title = "🧀 Cheese Squishy";

      hook = "นุ่มเด้งจนอยากบีบทั้งวัน 💛";

      caption = '''
🧀 สกุชชี่ชีสนุ่มเด้ง บีบเพลินสุด ๆ

✨ เนื้อนุ่ม คืนตัวช้า
💖 ช่วยคลายเครียดระหว่างวัน
🎁 เหมาะซื้อใช้เองหรือเป็นของขวัญ
📱 ถ่ายคลิปก็ขึ้นกล้องสุด ๆ

ใครเป็นสายของน่ารักต้องมีติดโต๊ะเลย!
''';

      hashtags = const [
        "#Squishy",
        "#Cheese",
        "#CuteToy",
        "#DeskSetup",
        "#SoloForgeAI",
      ];
    } else if (lower.contains('capybara')) {
      title = "🦫 Capybara Collection";

      hook = "ฮีลใจทุกครั้งที่มอง 🧡";

      caption = '''
🦫 ของสะสมคาปิบาราสุดน่ารัก

🌿 ฮีลใจทุกวัน
📚 เหมาะตั้งโต๊ะทำงาน
🎁 ของขวัญสำหรับคนรักคาปิบารา
📸 ถ่ายรูปสวยทุกมุม
''';

      hashtags = const [
        "#Capybara",
        "#Cute",
        "#DeskDecor",
        "#SoloForgeAI",
      ];
    } else if (lower.contains('bread') ||
        lower.contains('toast') ||
        lower.contains('ขนมปัง')) {
      title = "🍞 Bread Squishy";

      hook = "นุ่มเหมือนขนมปังจริง 🍞";

      caption = '''
🍞 สกุชชี่ขนมปังสุดนุ่ม

💛 บีบสนุก
✨ คืนตัวช้า
🎁 ของขวัญสุดน่ารัก
📱 เหมาะทำคลิปสั้น
''';

      hashtags = const [
        "#Bread",
        "#Squishy",
        "#CuteToy",
        "#SoloForgeAI",
      ];
    } else {
      title = "✨ Affiliate Pick";

      hook = "ของดีที่อยากแนะนำวันนี้";

      caption = '''
✨ สินค้าน่าสนใจ

💖 คุณภาพดี
🔥 รีวิวดี
🎁 เหมาะใช้เองและเป็นของขวัญ

กดดูรายละเอียดเพิ่มเติมได้เลย
''';

      hashtags = const [
        "#Shopee",
        "#Affiliate",
        "#SoloForgeAI",
      ];
    }

    return GeneratedContent(
      title: title,
      hook: hook,
      caption: caption,
      hashtags: hashtags,
      callToAction: "🛒 กดลิงก์เพื่อดูรายละเอียดสินค้า",
      platform: platform,
      createdAt: DateTime.now(),
    );
  }
}
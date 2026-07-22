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
      const Duration(seconds: 2),
    );

    return GeneratedContent(
      title: "Mock Title",

      hook: "เห็นแล้วต้องหยุดดู! ของชิ้นนี้กำลังเป็นกระแส",

      caption: '''
✨ ใช้งานง่าย
💖 คุ้มค่ากับราคา
🔥 รีวิวดีจากผู้ใช้จริง

เหมาะสำหรับคนที่กำลังมองหาสินค้าคุณภาพในราคาสบายกระเป๋า
''',

      hashtags: const [
        "#Shopee",
        "#Affiliate",
        "#SoloForgeAI",
      ],

      callToAction:
          "กดลิงก์ด้านล่างเพื่อดูรายละเอียดสินค้า",

      platform: platform,

      createdAt: DateTime.now(),
    );
  }
}
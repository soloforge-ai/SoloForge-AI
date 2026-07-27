import '../models/affiliate_product.dart';
import '../models/forge_result.dart';

class AIForgeService {
  const AIForgeService();

  ForgeResult forge(AffiliateProduct product) {
    final hook = _buildHook(product);
    final caption = _buildCaption(product);
    final cta = _buildCTA(product);
    final script = _buildScript(hook, caption, cta);

    return ForgeResult(hook: hook, caption: caption, cta: cta, script: script);
  }

  String _buildHook(AffiliateProduct product) {
    if (product.miniBossScore >= 90) {
      return "🔥 ของดีที่ AI ให้คะแนน ${product.miniBossScore.toStringAsFixed(0)} คะแนน!";
    }

    if (product.miniBossScore >= 80) {
      return "⭐ คนซื้อพูดถึงเยอะ ลองดูตัวนี้ก่อน!";
    }

    if (product.sold > 500) {
      return "💥 ขายดีจนหลายคนเลือกซื้อ!";
    }

    if (product.price <= 100) {
      return "💰 ของดีราคาเบา น่าลองสุด ๆ";
    }

    return "✨ ${product.title}";
  }

  String _buildCaption(AffiliateProduct product) {
    return '''
${product.title}

🏪 ร้าน : ${product.shopName}

💵 ราคา : ${product.priceText}

📦 ขายแล้ว : ${product.soldText}

🤖 MiniBoss Score : ${product.miniBossScore.toStringAsFixed(1)}

ลองดูรายละเอียดเพิ่มเติมได้จากลิงก์ด้านล่าง
''';
  }

  String _buildCTA(AffiliateProduct product) {
    return "👉 กดดูสินค้าได้เลย\n${product.productUrl}";
  }

  String _buildScript(String hook, String caption, String cta) {
    return '''
$hook

$caption

$cta
''';
  }
}

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/affiliate_content_package.dart';

void main() {
  test('AffiliateContentPackage parses claim gate and end card', () {
    final package = AffiliateContentPackage.fromJson({
      'program_slug': 'tool-a',
      'program_name': 'Tool A',
      'platform': 'youtube_shorts',
      'format': 'review',
      'intent': 'commercial_investigation',
      'goal': 'affiliate_click',
      'title': 'ลอง Tool A',
      'hooks': ['ฮุค 1', 'ฮุค 2'],
      'script': 'ทดสอบก่อนสรุปผล',
      'shot_list': ['เปิดหน้าเครื่องมือ'],
      'voiceover': 'ลองใช้งานจริง',
      'visual_prompts': ['vertical AI workspace'],
      'thumbnail_brief': 'Tool A ดีไหม?',
      'cta': 'ดูรายละเอียดที่ลิงก์',
      'description': 'รายละเอียดคลิป',
      'affiliate_disclosure': 'มีลิงก์ Affiliate',
      'claims': [
        {
          'claim_text': 'ประหยัดเวลา 70%',
          'claim_type': 'measured_result',
          'evidence_required': 'ต้องจับเวลาก่อนและหลัง',
          'verification_status': 'unverified',
        }
      ],
      'tools': [
        {
          'tool_name': 'Pollinations (openai)',
          'role': 'Script / Content Draft',
          'used_in_final_output': true,
        }
      ],
      'end_card': {
        'heading': 'เบื้องหลังคลิปนี้',
        'items': [
          {'role': 'Script', 'tool': 'Pollinations (openai)'}
        ],
        'closing': 'ทดลองจริง ใช้จริง แล้วค่อยเล่า',
      },
    });

    expect(package.title, 'ลอง Tool A');
    expect(package.hasUnverifiedClaims, isTrue);
    expect(package.claims.single.claimType, 'measured_result');
    expect(package.tools.single.usedInFinalOutput, isTrue);
    expect(package.endCardClosing, 'ทดลองจริง ใช้จริง แล้วค่อยเล่า');
    expect(package.toCopyableText(), contains('AFFILIATE DISCLOSURE'));
  });
}

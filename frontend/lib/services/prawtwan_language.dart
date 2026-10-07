import 'package:flutter/widgets.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// UI language only: conversation text and the existing agent stay unchanged.
class PrawtwanCopy {
  const PrawtwanCopy(this.code);
  factory PrawtwanCopy.forLocale(Locale locale) =>
      PrawtwanCopy(locale.languageCode == 'th' ? 'th' : 'en');

  final String code;
  bool get _thai => code == 'th';
  String get name => _thai ? 'พี่พราว' : 'Prawtwan';
  String get title => _thai ? 'คุยกับพี่พราว' : 'Chat with Prawtwan';
  String get subtitle => _thai ? 'ผู้ช่วยงานเขียนนิยาย' : 'Fiction editor';
  String get clear => _thai ? 'ล้างบทสนทนา' : 'Clear chat';
  String get send => _thai ? 'ส่งข้อความ' : 'Send message';
  String get you => _thai ? 'คุณ' : 'You';
  String get privacy => _thai
      ? 'บทสนทนาเฉพาะเซสชันนี้ • ใช้ Pollen เมื่อส่งข้อความเท่านั้น'
      : 'Session-only chat • Pollen is used only when you send';
  String get emptyTitle => _thai ? 'พี่พราวพร้อมแล้ว' : 'Prawtwan is ready';
  String get emptyBody => _thai
      ? 'ส่งฉาก บทสนทนา หรือคำถามเกี่ยวกับงานเขียนให้พี่พราวอ่านได้เลย'
      : 'Share a scene, dialogue, or a writing question with Prawtwan.';
  String get hint => _thai
      ? 'พิมพ์ข้อความหรือวางฉากให้พี่พราวอ่าน...'
      : 'Type a message or paste a scene for Prawtwan...';
  String get thinking =>
      _thai ? 'พี่พราวกำลังอ่าน...' : 'Prawtwan is reading...';
  String get unavailable => _thai
      ? 'พี่พราวไม่พร้อมให้บริการชั่วคราว กรุณาลองใหม่ภายหลัง'
      : 'Prawtwan is temporarily unavailable. Please try again later.';
  String get connect => _thai
      ? 'กรุณาเชื่อมต่อ Pollinations จากหน้า Home ก่อนคุยกับพี่พราว'
      : 'Connect Pollinations from Home before chatting with Prawtwan.';
  String get saveError => _thai
      ? 'บันทึกภาษาไม่ได้ ภาษานี้จะใช้เฉพาะครั้งนี้'
      : 'Could not save your language. It will apply for this visit only.';

  String error(String message) {
    if (message.contains('Connect Pollinations') ||
        message.contains('(401)') ||
        message.contains('(403)')) {
      return connect;
    }
    if (message.contains('too large')) {
      return _thai
          ? 'บทสนทนายาวเกินไป กรุณาล้างบทสนทนาหรือส่งข้อความให้สั้นลง'
          : 'The chat context is too large. Clear the chat or send a shorter excerpt.';
    }
    if (message.contains('did not respond in time')) {
      return _thai
          ? 'พี่พราวตอบไม่ทันเวลา กรุณาลองใหม่ภายหลัง'
          : 'Prawtwan did not respond in time. Please try again later.';
    }
    if (message.contains('empty response') ||
        message.contains('invalid response')) {
      return _thai
          ? 'ได้รับคำตอบที่ไม่สมบูรณ์จากพี่พราว กรุณาลองใหม่ภายหลัง'
          : 'Prawtwan returned an incomplete response. Please try again later.';
    }
    // Never expose arbitrary upstream details in the chat UI.
    return unavailable;
  }
}

class PrawtwanLanguagePreference {
  static const key = 'prawtwan_ui_language';
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Future<String?> read() async {
    try {
      final code = await _storage.read(key: key);
      return code == 'th' || code == 'en' ? code : null;
    } catch (_) {
      return null; // Device locale remains usable when storage is unavailable.
    }
  }

  Future<bool> write(String code) async {
    try {
      await _storage.write(key: key, value: code);
      return true;
    } catch (_) {
      return false;
    }
  }
}

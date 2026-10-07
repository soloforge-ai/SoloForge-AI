import 'dart:convert';
import 'dart:js_interop';

@JS('window.sessionStorage')
external _TabStorage get _storage;

extension type _TabStorage(JSObject _) implements JSObject {
  external JSString? getItem(JSString key);
  external void setItem(JSString key, JSString value);
  external void removeItem(JSString key);
}

const _key = 'soloforge.prawtwan.oauth-return';

bool savePrawtwanReturn(Map<String, dynamic> snapshot) {
  try {
    _storage.setItem(_key.toJS, jsonEncode(snapshot).toJS);
    return true;
  } catch (_) {
    return false;
  }
}

Map<String, dynamic>? takePrawtwanReturn() {
  try {
    final raw = _storage.getItem(_key.toJS)?.toDart;
    _storage.removeItem(_key.toJS);
    if (raw == null) return null;
    final data = jsonDecode(raw) as Map<String, dynamic>;
    if (!['th', 'en'].contains(data['language']) ||
        data['draft'] is! String ||
        data['messages'] is! List) {
      return null;
    }
    for (final message in data['messages'] as List) {
      if (message is! Map ||
          !['user', 'assistant'].contains(message['role']) ||
          message['content'] is! String) {
        return null;
      }
    }
    return data;
  } catch (_) {
    return null;
  }
}

void clearPrawtwanReturn() {
  try {
    _storage.removeItem(_key.toJS);
  } catch (_) {
    // Chat remains usable even when browser storage is unavailable.
  }
}

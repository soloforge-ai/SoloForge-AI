// Compile with `dart compile js` and run with browser-compatible sessionStorage.
import 'dart:convert';
import 'dart:js_interop';

import 'package:frontend/services/prawtwan_oauth_return.dart';

@JS('window.sessionStorage.setItem')
external void _setItem(JSString key, JSString value);

void check(bool condition, String message) {
  if (!condition) throw StateError(message);
}

void main() {
  final snapshot = {
    'language': 'th',
    'draft': 'Unsent scene',
    'messages': [
      {'role': 'user', 'content': 'Scene'},
      {'role': 'assistant', 'content': 'Feedback'},
    ],
  };
  check(savePrawtwanReturn(snapshot), 'Snapshot must save');
  check(
    jsonEncode(takePrawtwanReturn()) == jsonEncode(snapshot),
    'Snapshot must survive redirect',
  );
  check(takePrawtwanReturn() == null, 'Snapshot must be consumed once');
  check(savePrawtwanReturn(snapshot), 'Snapshot must save again');
  clearPrawtwanReturn();
  check(
    takePrawtwanReturn() == null,
    'Successful connection must clear snapshot',
  );
  _setItem('soloforge.prawtwan.oauth-return'.toJS, '{bad'.toJS);
  check(takePrawtwanReturn() == null, 'Malformed data must be ignored');
  check(
    savePrawtwanReturn({'language': 'bad', 'draft': '', 'messages': []}),
    'Test fixture must save',
  );
  check(takePrawtwanReturn() == null, 'Invalid language must be ignored');
}

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'pollinations_session_service.dart';

class PrawtwanMessage {
  const PrawtwanMessage({
    required this.role,
    required this.content,
  });

  final String role;
  final String content;

  Map<String, dynamic> toJson() => {
        'role': role,
        'content': content,
      };
}

class PrawtwanChatService {
  PrawtwanChatService({
    http.Client? client,
    PollinationsSessionService? sessionService,
  })  : _client = client ?? http.Client(),
        _sessionService = sessionService ?? PollinationsSessionService();

  static const int _maxContextMessages = 20;

  final http.Client _client;
  final PollinationsSessionService _sessionService;

  Future<String> send(List<PrawtwanMessage> messages) async {
    if (messages.isEmpty) {
      throw const PrawtwanChatException('Type a message before sending.');
    }

    final headers = await _sessionService.authorizationHeaders();
    final baseUrl = assetForgeApiUrl.trim().replaceFirst(RegExp(r'/$'), '');
    final contextMessages = messages.length <= _maxContextMessages
        ? messages
        : messages.sublist(messages.length - _maxContextMessages);

    final response = await _client.post(
      Uri.parse('$baseUrl/v1/prawtwan/chat'),
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'messages': contextMessages.map((message) => message.toJson()).toList(),
      }),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw PrawtwanChatException(_errorMessage(response));
    }

    try {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final message = body['message']?.toString().trim() ?? '';
      if (message.isEmpty) {
        throw const PrawtwanChatException('Prawtwan returned an empty response.');
      }
      return message;
    } on FormatException {
      throw const PrawtwanChatException('Prawtwan returned an invalid response.');
    }
  }

  Future<void> dispose() async {
    _client.close();
    await _sessionService.dispose();
  }

  String _errorMessage(http.Response response) {
    try {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final detail = body['detail'];
      if (detail is String && detail.trim().isNotEmpty) {
        return detail;
      }
      if (detail is List && detail.isNotEmpty) {
        return 'The chat context is too large. Clear the chat or send a shorter excerpt.';
      }
    } catch (_) {
      // Fall through to the safe generic error below.
    }
    return 'Chat Prawtwan failed (${response.statusCode}).';
  }
}

class PrawtwanChatException implements Exception {
  const PrawtwanChatException(this.message);

  final String message;

  @override
  String toString() => message;
}

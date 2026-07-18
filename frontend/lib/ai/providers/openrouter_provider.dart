import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../models/generated_content.dart';
import '../platforms.dart';
import 'ai_provider.dart';

class OpenRouterProvider implements AIProvider {
  static const String _defaultApiUrl =
      'https://openrouter.ai/api/v1/chat/completions';
  static const String _defaultModel = 'openai/gpt-4o-mini';

  final String apiKey;
  final String model;
  final Uri apiUrl;
  final http.Client _client;

  OpenRouterProvider({
    String apiKey = const String.fromEnvironment('OPENROUTER_API_KEY'),
    String model = _defaultModel,
    String apiUrl = _defaultApiUrl,
    http.Client? client,
  })  : apiKey = apiKey,
        model = model,
        apiUrl = Uri.parse(apiUrl),
        _client = client ?? http.Client();

  @override
  Future<GeneratedContent> generateContent({
    required String prompt,
    required PlatformType platform,
  }) async {
    if (apiKey.trim().isEmpty) {
      throw const AIProviderException('OpenRouter API key is not configured.');
    }

    try {
      final response = await _client.post(
        apiUrl,
        headers: {
          'Authorization': 'Bearer $apiKey',
          'Content-Type': 'application/json',
          'HTTP-Referer': 'https://soloforge.ai',
          'X-Title': 'SoloForge AI',
        },
        body: jsonEncode({
          'model': model,
          'messages': [
            {
              'role': 'system',
              'content': _systemPrompt,
            },
            {
              'role': 'user',
              'content': prompt,
            },
          ],
          'response_format': {'type': 'json_object'},
        }),
      );

      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw AIProviderException(
          'OpenRouter request failed with status ${response.statusCode}.',
          response.body,
        );
      }

      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final choices = body['choices'];
      if (choices is! List || choices.isEmpty) {
        throw const AIProviderException('OpenRouter returned no choices.');
      }

      final message = choices.first['message'];
      if (message is! Map<String, dynamic>) {
        throw const AIProviderException('OpenRouter response is missing message.');
      }

      final content = message['content'];
      if (content is! String || content.trim().isEmpty) {
        throw const AIProviderException('OpenRouter response is empty.');
      }

      return _contentFromJson(content, platform);
    } on AIProviderException {
      rethrow;
    } on FormatException catch (error) {
      throw AIProviderException('OpenRouter returned invalid JSON.', error);
    } catch (error) {
      throw AIProviderException('OpenRouter request failed.', error);
    }
  }

  GeneratedContent _contentFromJson(String rawContent, PlatformType platform) {
    final decoded = jsonDecode(rawContent) as Map<String, dynamic>;

    return GeneratedContent(
      title: _readString(decoded, 'title'),
      hook: _readString(decoded, 'hook'),
      caption: _readString(decoded, 'caption'),
      hashtags: _readStringList(decoded, 'hashtags'),
      callToAction: _readString(decoded, 'callToAction'),
      platform: platform,
      createdAt: DateTime.now(),
    );
  }

  String _readString(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is String) {
      return value.trim();
    }

    return '';
  }

  List<String> _readStringList(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is List) {
      return value.whereType<String>().map((item) => item.trim()).where(
        (item) {
          return item.isNotEmpty;
        },
      ).toList(growable: false);
    }

    return const [];
  }
}

const String _systemPrompt = '''
You generate affiliate marketing content for SoloForge AI.
Return only a valid JSON object with these keys:
- title: string
- hook: string
- caption: string
- hashtags: string array
- callToAction: string
Do not include markdown, comments, or additional keys.
''';

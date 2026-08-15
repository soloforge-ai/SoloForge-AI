import 'dart:typed_data';

import 'package:http/http.dart' as http;

/// Minimal Pollinations image-generation client for SoloForge AI.
///
/// Authentication is intentionally supplied at runtime. Never hard-code a
/// Pollinations secret key in the Flutter source code or repository.
class PollinationsImageService {
  const PollinationsImageService({this.baseUrl = 'https://gen.pollinations.ai'});

  final String baseUrl;

  /// Generates an image and returns the raw image bytes.
  ///
  /// [apiKey] should be supplied by the authenticated user/session. For a
  /// production web app, prefer Pollinations BYOP/OAuth rather than shipping
  /// a server secret in the client.
  Future<Uint8List> generateImage({
    required String prompt,
    required String apiKey,
    String model = 'flux',
    int width = 1024,
    int height = 1024,
    int? seed,
    bool transparent = false,
  }) async {
    final uri = _buildImageUri(
      prompt: prompt,
      model: model,
      width: width,
      height: height,
      seed: seed,
      transparent: transparent,
    );

    final response = await http.get(
      uri,
      headers: <String, String>{
        'Authorization': 'Bearer $apiKey',
        'Accept': 'image/png,image/jpeg,image/*',
      },
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw PollinationsImageException(
        'Image generation failed (${response.statusCode}): '
        '${_cleanError(response.body)}',
        statusCode: response.statusCode,
      );
    }

    if (response.bodyBytes.isEmpty) {
      throw const PollinationsImageException('Pollinations returned an empty image.');
    }

    return response.bodyBytes;
  }

  /// Builds a Pollinations image URL without making a network request.
  /// Useful for previews or when the app wants the browser to load the image.
  Uri buildImageUri({
    required String prompt,
    String model = 'flux',
    int width = 1024,
    int height = 1024,
    int? seed,
    bool transparent = false,
  }) {
    return _buildImageUri(
      prompt: prompt,
      model: model,
      width: width,
      height: height,
      seed: seed,
      transparent: transparent,
    );
  }

  Uri _buildImageUri({
    required String prompt,
    required String model,
    required int width,
    required int height,
    required int? seed,
    required bool transparent,
  }) {
    if (prompt.trim().isEmpty) {
      throw const PollinationsImageException('Prompt cannot be empty.');
    }
    if (width <= 0 || height <= 0) {
      throw const PollinationsImageException('Image width and height must be positive.');
    }

    final encodedPrompt = Uri.encodeComponent(prompt.trim());
    final query = <String, String>{
      'model': model,
      'width': width.toString(),
      'height': height.toString(),
      'transparent': transparent.toString(),
      if (seed != null) 'seed': seed.toString(),
    };

    return Uri.parse('$baseUrl/image/$encodedPrompt').replace(queryParameters: query);
  }

  String _cleanError(String body) {
    if (body.trim().isEmpty) return 'Unknown error';
    final normalized = body.replaceAll(RegExp(r'\s+'), ' ').trim();
    return normalized.length > 500 ? '${normalized.substring(0, 500)}…' : normalized;
  }
}

class PollinationsImageException implements Exception {
  const PollinationsImageException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

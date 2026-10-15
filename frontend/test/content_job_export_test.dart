import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/content_job_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const signedUrl = 'https://storage.example.com/storage/v1/object/sign/content-assets/job/cover.png?token=test';
const preview = ContentAssetPreview(url: signedUrl, mediaType: 'image', assetStatus: 'READY', pipelineRoute: 'IMAGE');

void main() {
  final png = Uint8List.fromList([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1]);
  test('downloads valid signed PNG without authorization header', () async {
    final service = ContentJobService(client: MockClient((request) async {
      expect(request.headers.containsKey('Authorization'), isFalse);
      return http.Response.bytes(png, 200, headers: {'content-type': 'image/png'});
    }));
    expect(await service.downloadReadyImage(preview), png);
  });
  test('rejects HTML response masquerading as an image', () async {
    final service = ContentJobService(client: MockClient((_) async =>
      http.Response('<html>error</html>', 200, headers: {'content-type': 'image/png'})));
    expect(service.downloadReadyImage(preview), throwsFormatException);
  });
  test('rejects expired signed URL HTTP response', () async {
    final service = ContentJobService(client: MockClient((_) async => http.Response('expired', 403)));
    expect(service.downloadReadyImage(preview), throwsException);
  });
  test('rejects insecure or non-storage URLs before request', () async {
    final service = ContentJobService(client: MockClient((_) async => throw StateError('unexpected network call')));
    const invalid = ContentAssetPreview(url: 'http://example.com/image.png', mediaType: 'image', assetStatus: 'READY', pipelineRoute: 'IMAGE');
    expect(service.downloadReadyImage(invalid), throwsFormatException);
  });
  test('rejects non-image assets', () async {
    final service = ContentJobService(client: MockClient((_) async => throw StateError('unexpected network call')));
    const video = ContentAssetPreview(url: signedUrl, mediaType: 'video', assetStatus: 'READY', pipelineRoute: 'VIDEO');
    expect(service.downloadReadyImage(video), throwsFormatException);
  });
}

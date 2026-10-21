import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/content_job_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const signedUrl = 'https://storage.example.com/storage/v1/object/sign/content-assets/job/cover.png?token=test';
const preview = ContentAssetPreview(url: signedUrl, mediaType: 'image', assetStatus: 'READY', pipelineRoute: 'IMAGE');

ContentJobService exportService(http.Client client) => ContentJobService(
  client: client,
  storageOrigin: 'https://storage.example.com',
);

void main() {
  final png = Uint8List.fromList([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1]);
  test('downloads valid signed PNG without authorization header', () async {
    final service = exportService(MockClient((request) async {
      expect(request.headers.containsKey('Authorization'), isFalse);
      return http.Response.bytes(png, 200, headers: {'content-type': 'image/png'});
    }));
    expect(await service.downloadReadyImage(preview), png);
  });
  test('rejects HTML response masquerading as an image', () async {
    final service = exportService(MockClient((_) async =>
      http.Response('<html>error</html>', 200, headers: {'content-type': 'image/png'})));
    expect(service.downloadReadyImage(preview), throwsFormatException);
  });
  test('rejects expired signed URL HTTP response', () async {
    final service = exportService(MockClient((_) async => http.Response('expired', 403)));
    expect(service.downloadReadyImage(preview), throwsException);
  });
  test('rejects insecure or non-storage URLs before request', () async {
    final service = exportService(MockClient((_) async => throw StateError('unexpected network call')));
    const invalid = ContentAssetPreview(url: 'http://example.com/image.png', mediaType: 'image', assetStatus: 'READY', pipelineRoute: 'IMAGE');
    expect(service.downloadReadyImage(invalid), throwsFormatException);
  });
  test('rejects foreign HTTPS origin even with matching storage path', () async {
    final service = exportService(MockClient((_) async => throw StateError('unexpected network call')));
    const malicious = ContentAssetPreview(url: 'https://untrusted.example/storage/v1/object/sign/content-assets/job/cover.png?token=leak', mediaType: 'image', assetStatus: 'READY', pipelineRoute: 'IMAGE');
    expect(service.downloadReadyImage(malicious), throwsFormatException);
  });
  test('rejects missing signed token', () async {
    final service = exportService(MockClient((_) async => throw StateError('unexpected network call')));
    const unsigned = ContentAssetPreview(url: 'https://storage.example.com/storage/v1/object/sign/content-assets/job/cover.png', mediaType: 'image', assetStatus: 'READY', pipelineRoute: 'IMAGE');
    expect(service.downloadReadyImage(unsigned), throwsFormatException);
  });
  test('rejects a path containing a signed storage substring', () async {
    final service = exportService(MockClient((_) async => throw StateError('unexpected network call')));
    const spoof = ContentAssetPreview(url: 'https://storage.example.com/redirect/storage/v1/object/sign/content-assets/job/cover.png?token=leak', mediaType: 'image', assetStatus: 'READY', pipelineRoute: 'IMAGE');
    expect(service.downloadReadyImage(spoof), throwsFormatException);
  });
  test('rejects mismatched MIME and image signature', () async {
    final service = exportService(MockClient((_) async => http.Response.bytes(
      Uint8List.fromList([0xff, 0xd8, 0xff, 0x00]), 200,
      headers: {'content-type': 'image/png'},
    )));
    expect(service.downloadReadyImage(preview), throwsFormatException);
  });
  test('accepts JPEG image with matching MIME and signature', () async {
    final jpeg = Uint8List.fromList([0xff, 0xd8, 0xff, 0x00]);
    final service = exportService(MockClient((_) async => http.Response.bytes(
      jpeg, 200, headers: {'content-type': 'image/jpeg'},
    )));
    expect(await service.downloadReadyImage(preview), jpeg);
  });
  test('rejects image exceeding the size limit', () async {
    final service = exportService(MockClient((_) async => http.Response.bytes(
      Uint8List(20 * 1024 * 1024 + 1), 200,
      headers: {'content-type': 'image/png'},
    )));
    expect(service.downloadReadyImage(preview), throwsFormatException);
  });
  test('rejects non-image assets', () async {
    final service = exportService(MockClient((_) async => throw StateError('unexpected network call')));
    const video = ContentAssetPreview(url: signedUrl, mediaType: 'video', assetStatus: 'READY', pipelineRoute: 'VIDEO');
    expect(service.downloadReadyImage(video), throwsFormatException);
  });
}

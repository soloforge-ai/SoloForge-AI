import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/pages/owner_oauth_uat_page.dart';

void main() {
  test('web owner OAuth redirect uses the current HTTPS origin', () {
    final redirect = ownerOAuthRedirectTo(
      isWeb: true,
      currentUri: Uri.parse('https://soloforge-ai-web.onrender.com/some/path?x=1#frag'),
    );

    expect(redirect, 'https://soloforge-ai-web.onrender.com');
  });

  test('mobile owner OAuth redirect keeps the SoloForge custom scheme', () {
    final redirect = ownerOAuthRedirectTo(
      isWeb: false,
      currentUri: Uri.parse('https://soloforge-ai-web.onrender.com'),
    );

    expect(redirect, 'soloforge://oauth/supabase');
  });

  test('web owner OAuth redirect rejects non-http schemes', () {
    expect(
      () => ownerOAuthRedirectTo(
        isWeb: true,
        currentUri: Uri.parse('soloforge://oauth/supabase'),
      ),
      throwsArgumentError,
    );
  });
}

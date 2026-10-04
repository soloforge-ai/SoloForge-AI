import 'dart:async';

import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// Identity-only UAT. Never exchanges an anonymous or unverified user for an
/// owner-capable SoloForge backend session.
class OwnerOAuthUatPage extends StatefulWidget {
  const OwnerOAuthUatPage({super.key, this.identityOnly = true, this.onRetry, this.ownerAccessMessage});

  final bool identityOnly;
  final VoidCallback? onRetry;
  final String? ownerAccessMessage;

  @override
  State<OwnerOAuthUatPage> createState() => _OwnerOAuthUatPageState();
}

class _OwnerOAuthUatPageState extends State<OwnerOAuthUatPage> {
  StreamSubscription<AuthState>? _subscription;
  Session? _session;
  bool _opening = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final auth = Supabase.instance.client.auth;
    _session = auth.currentSession;
    _subscription = auth.onAuthStateChange.listen((state) {
      if (!mounted) return;
      setState(() {
        _session = state.session;
        _opening = false;
        _error = null;
      });
    }, onError: (Object error) {
      if (mounted) setState(() { _opening = false; _error = 'Sign-in failed. Please try again.'; });
    });
  }

  Future<void> _signIn() async {
    setState(() { _opening = true; _error = null; });
    try {
      final launched = await Supabase.instance.client.auth.signInWithOAuth(
        OAuthProvider.github,
        redirectTo: 'soloforge://oauth/supabase',
        authScreenLaunchMode: LaunchMode.externalApplication,
      );
      if (mounted) {
        setState(() {
          _opening = false;
          if (!launched) _error = 'Could not open GitHub sign-in.';
        });
      }
    } catch (_) {
      if (mounted) setState(() { _opening = false; _error = 'Could not start GitHub sign-in.'; });
    }
  }

  Future<void> _signOut() async {
    await Supabase.instance.client.auth.signOut();
    if (mounted) setState(() { _session = null; _opening = false; });
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final user = _session?.user;
    return Scaffold(
      appBar: AppBar(title: const Text('SoloForge owner sign-in test')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.verified_user_outlined, size: 56),
              const SizedBox(height: 20),
              if (user == null) ...[
                const Text('Sign in with your GitHub account to verify the SoloForge owner identity.',
                    textAlign: TextAlign.center),
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: _opening ? null : _signIn,
                  child: Text(_opening ? 'Opening GitHub…' : 'Continue with GitHub'),
                ),
              ] else ...[
                Text(widget.identityOnly
                    ? 'Supabase authentication succeeded. Owner access remains locked during this test.'
                    : (widget.ownerAccessMessage ?? 'Owner access is unavailable. Please retry.'),
                    textAlign: TextAlign.center),
                const SizedBox(height: 16),
                SelectableText('Supabase user ID: ${user.id}', textAlign: TextAlign.center),
                const SizedBox(height: 20),
                if (!widget.identityOnly)
                  FilledButton(onPressed: widget.onRetry, child: const Text('Retry owner access')),
                OutlinedButton(onPressed: _signOut, child: const Text('Sign out')),
              ],
              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

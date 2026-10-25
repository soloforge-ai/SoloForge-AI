import 'package:flutter/material.dart';
import '../services/owner_v2_session_service.dart';

class OwnerV2LoginPage extends StatefulWidget {
  const OwnerV2LoginPage({super.key, required this.session, required this.onAuthenticated});
  final OwnerV2SessionService session;
  final VoidCallback onAuthenticated;
  @override
  State<OwnerV2LoginPage> createState() => _OwnerV2LoginPageState();
}

class _OwnerV2LoginPageState extends State<OwnerV2LoginPage> {
  final _email = TextEditingController();
  final _code = TextEditingController();
  OwnerV2Challenge? _challenge;
  bool _busy = false;
  String? _error;

  Future<void> _run(Future<void> Function() action) async {
    if (_busy) return;
    setState(() { _busy = true; _error = null; });
    try {
      await action();
    } on OwnerV2Exception catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Sign-in failed. Please retry.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _email.dispose();
    _code.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('SoloForge Owner Login')),
    body: Center(child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 440),
      child: Padding(padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.lock_outline, size: 48),
          const SizedBox(height: 20),
          if (_challenge == null) ...[
            TextField(controller: _email, keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(labelText: 'Owner email')),
            const SizedBox(height: 16),
            FilledButton(onPressed: _busy ? null : () => _run(() async {
              final challenge = await widget.session.request(_email.text.trim());
              if (mounted) setState(() => _challenge = challenge);
            }), child: const Text('Send sign-in code')),
          ] else ...[
            const Text('Enter the 43-character code sent to the owner email.'),
            const SizedBox(height: 16),
            TextField(controller: _code, autocorrect: false, enableSuggestions: false,
              decoration: const InputDecoration(labelText: 'One-time code')),
            const SizedBox(height: 16),
            FilledButton(onPressed: _busy ? null : () => _run(() async {
              await widget.session.verify(_challenge!, _code.text);
              if (mounted) widget.onAuthenticated();
            }), child: const Text('Verify and sign in')),
            TextButton(onPressed: _busy ? null : () => setState(() {
              _challenge = null;
              _code.clear();
            }), child: const Text('Start again')),
          ],
          if (_busy) const Padding(padding: EdgeInsets.all(12),
              child: CircularProgressIndicator()),
          if (_error != null) Padding(padding: const EdgeInsets.all(12),
              child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error))),
        ]),
      ),
    )),
  );
}

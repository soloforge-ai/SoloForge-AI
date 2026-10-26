import 'package:flutter/material.dart';

import '../services/owner_v2_session_service.dart';

class OwnerV2LoginPage extends StatefulWidget {
  const OwnerV2LoginPage({super.key, required this.sessions});
  final OwnerV2SessionService sessions;
  @override
  State<OwnerV2LoginPage> createState() => _OwnerV2LoginPageState();
}

class _OwnerV2LoginPageState extends State<OwnerV2LoginPage> {
  final _email = TextEditingController();
  final _code = TextEditingController();
  bool _sent = false;
  bool _busy = false;
  String? _message;

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      if (_sent) {
        await widget.sessions.verifyCode(_code.text);
      } else {
        await widget.sessions.requestCode(_email.text);
        if (mounted) {
          setState(() {
            _sent = true;
            _message =
                'If this email is registered, a code has been sent. Paste the full 43-character code within 10 minutes.';
          });
        }
      }
    } on OwnerV2Exception catch (error) {
      if (mounted) {
        setState(() {
          _message = error.message;
          _sent = false;
        });
      }
    } finally {
      if (mounted) _code.clear();
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
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
    appBar: AppBar(title: const Text('SoloForge owner sign-in')),
    body: Center(
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.verified_user_outlined, size: 56),
                const SizedBox(height: 20),
                TextField(
                  controller: _email,
                  enabled: !_busy && !_sent,
                  keyboardType: TextInputType.emailAddress,
                  autocorrect: false,
                  decoration: const InputDecoration(labelText: 'Owner email'),
                ),
                if (_sent)
                  TextField(
                    controller: _code,
                    enabled: !_busy,
                    obscureText: true,
                    autocorrect: false,
                    enableSuggestions: false,
                    decoration: const InputDecoration(
                      labelText: 'Email code (43 characters)',
                    ),
                  ),
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: _busy ? null : _submit,
                  child: Text(
                    _busy
                        ? 'Please wait…'
                        : (_sent ? 'Verify code' : 'Send email code'),
                  ),
                ),
                if (_sent)
                  TextButton(
                    onPressed: _busy
                        ? null
                        : () {
                            widget.sessions.clear();
                            _code.clear();
                            setState(() {
                              _sent = false;
                              _message = null;
                            });
                          },
                    child: const Text('Use another email / request a new code'),
                  ),
                if (_message != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 16),
                    child: Text(_message!, textAlign: TextAlign.center),
                  ),
                const SizedBox(height: 16),
                const Text(
                  'Sign-in does not authorize spending, generation or publishing.',
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

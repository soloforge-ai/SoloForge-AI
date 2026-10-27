import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../services/soloforge_session_service.dart';
import '../services/pollinations_session_service.dart';

/// Owner-scoped connection, evidence and verification. Spending remains disabled.
class PollinationsAccountInspectPage extends StatefulWidget {
  const PollinationsAccountInspectPage({
    super.key,
    this.client,
    this.ownerAuthorization,
  });

  final http.Client? client;
  final Future<Map<String, String>> Function()? ownerAuthorization;

  @override
  State<PollinationsAccountInspectPage> createState() =>
      _PollinationsAccountInspectPageState();
}

class _PollinationsAccountInspectPageState
    extends State<PollinationsAccountInspectPage> {
  final _sessions = SoloForgeSessionService(useOwnerV2: true);
  late final http.Client _client;

  Future<Map<String, String>> _headers() =>
      widget.ownerAuthorization?.call() ?? _sessions.authorizationHeaders();
  List<Map<String, dynamic>> _choices = [];
  String? _selected;
  Map<String, dynamic>? _result;
  String? _error;
  bool _busy = false;

  String get _base => assetForgeApiUrl.replaceFirst(RegExp(r'/$'), '');

  @override
  void initState() {
    super.initState();
    _client = widget.client ?? http.Client();
    _loadChoices();
  }

  Future<void> _loadChoices() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final headers = await _headers();
      final response = await _client
          .get(
            Uri.parse('$_base/auth/pollinations/account/credentials'),
            headers: headers,
          )
          .timeout(const Duration(seconds: 20));
      if (response.statusCode != 200) {
        throw Exception(
          'Could not load stored credentials (HTTP ${response.statusCode}).',
        );
      }
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final choices = (body['credentials'] as List)
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList();
      if (!mounted) return;
      setState(() {
        _choices = choices;
        _selected = choices.length == 1 ? choices.first['id'] as String? : null;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _reverify() async {
    if (_selected == null || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final headers = await _headers();
      final response = await _client
          .post(
            Uri.parse('$_base/auth/pollinations/sk/reverify'),
            headers: {...headers, 'Content-Type': 'application/json'},
            body: jsonEncode({'credential_record_id': _selected}),
          )
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) {
        throw Exception(
          'Verification unconfirmed (HTTP ${response.statusCode}). Reload credentials.',
        );
      }
      if (mounted) {
        setState(
          () => _result = jsonDecode(response.body) as Map<String, dynamic>,
        );
        await _loadChoices();
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _error =
              'Verification unconfirmed. Reload credentials before trying again.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _claim() async {
    final input = await showDialog<_CredentialSubmission>(
      context: context,
      builder: (_) => const _CredentialDialog(),
    );
    if (input == null || !mounted) return;
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final headers = await _headers();
      final response = await _client
          .post(
            Uri.parse(
              '$_base/auth/pollinations/sk/${input.recordId.isEmpty ? 'submit' : 'claim'}',
            ),
            headers: {...headers, 'Content-Type': 'application/json'},
            body: jsonEncode({
              if (input.recordId.isNotEmpty)
                'credential_record_id': input.recordId,
              'access_token': input.token,
            }),
          )
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) throw Exception('Claim unconfirmed.');
      if (mounted) {
        setState(
          () => _result = jsonDecode(response.body) as Map<String, dynamic>,
        );
        await _loadChoices();
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _error =
              'Claim not completed. Check account evidence and reload credentials.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _connect() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final provider = PollinationsSessionService();
    try {
      await provider.connect();
    } catch (_) {
      if (mounted) {
        setState(
          () => _error =
              'Connection unavailable. Sign in with Owner V2 and try again.',
        );
      }
    } finally {
      await provider.dispose();
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _inspect() async {
    final id = _selected;
    if (id == null || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final headers = await _headers();
      final uri = Uri.parse(
        '$_base/auth/pollinations/account/inspect',
      ).replace(queryParameters: {'credential_record_id': id});
      final response = await _client
          .get(uri, headers: headers)
          .timeout(const Duration(seconds: 50));
      if (response.statusCode != 200) {
        throw Exception('Inspection failed (HTTP ${response.statusCode}).');
      }
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      if (mounted) setState(() => _result = body);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _sessions.dispose();
    _client.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Inspect Pollinations Account')),
    body: ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const Text('Connect and verify ownership. Spending stays disabled.'),
        TextButton(
          onPressed: _busy ? null : _connect,
          child: const Text('Connect Pollinations'),
        ),
        TextButton(
          onPressed: _busy ? null : _loadChoices,
          child: const Text('Reload credentials'),
        ),
        TextButton(
          onPressed: _busy ? null : _claim,
          child: const Text('Submit or claim existing SK'),
        ),
        const SizedBox(height: 16),
        if (_busy) const LinearProgressIndicator(),
        if (_choices.isEmpty)
          const Text('No active stored credentials loaded.'),
        if (_choices.isNotEmpty)
          DropdownButtonFormField<String>(
            key: ValueKey(_selected),
            initialValue: _selected,
            decoration: const InputDecoration(
              labelText: 'Existing credential record',
            ),
            items: _choices.map((row) {
              final id = row['id']?.toString() ?? '';
              return DropdownMenuItem(
                value: id,
                child: Text(
                  '${id.substring(0, id.length < 8 ? id.length : 8)}…  ${row['verification_status'] ?? 'PENDING_VERIFICATION'}',
                ),
              );
            }).toList(),
            onChanged: _busy
                ? null
                : (value) => setState(() => _selected = value),
          ),
        const SizedBox(height: 12),
        FilledButton(
          onPressed: _busy || _selected == null ? null : _inspect,
          child: const Text('Inspect existing account'),
        ),
        FilledButton(
          onPressed: _busy || _selected == null ? null : _reverify,
          child: const Text('Verify provider ownership'),
        ),
        if (_error != null)
          Text(_error!, style: const TextStyle(color: Colors.redAccent)),
        if (_result != null) ...[
          const SizedBox(height: 16),
          Text(
            'State: ${_result!['verification_status'] ?? _result!['state'] ?? 'UNKNOWN'}',
          ),
          if (_result!['verification_outcome'] != null)
            Text('Verification: ${_result!['verification_outcome']}'),
          Text(
            'Provider subject: ${_result!['provider_subject'] ?? 'Unavailable'}',
          ),
          Text(
            'Owner binding: ${_result!['provider_ownership_verified'] == true ? 'VERIFIED' : _result!['owner_binding'] ?? 'UNVERIFIED'}',
          ),
          Text(
            'Spending authorized: ${_result!['spending_authorized'] == true ? 'Yes' : 'No'}',
          ),
          const SizedBox(height: 12),
          for (final name in ['identity', 'key', 'balance', 'usage'])
            ListTile(
              title: Text(name),
              subtitle: Text(
                jsonEncode((_result!['evidence'] as Map?)?[name] ?? {}),
              ),
            ),
        ],
      ],
    ),
  );
}

class _CredentialSubmission {
  const _CredentialSubmission(this.recordId, this.token);
  final String recordId;
  final String token;
}

class _CredentialDialog extends StatefulWidget {
  const _CredentialDialog();
  @override
  State<_CredentialDialog> createState() => _CredentialDialogState();
}

class _CredentialDialogState extends State<_CredentialDialog> {
  final _record = TextEditingController();
  final _secret = TextEditingController();
  @override
  void dispose() {
    _record.dispose();
    _secret.clear();
    _secret.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Submit or claim existing SK'),
    content: SingleChildScrollView(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'Leave record ID empty to submit an SK as Pending. Claiming a legacy record requires independent account evidence. Spending stays disabled.',
          ),
          TextField(
            controller: _record,
            decoration: const InputDecoration(
              labelText: 'Legacy record ID (optional)',
            ),
          ),
          TextField(
            controller: _secret,
            obscureText: true,
            enableSuggestions: false,
            autocorrect: false,
            decoration: const InputDecoration(labelText: 'Existing SK'),
          ),
        ],
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Cancel'),
      ),
      TextButton(
        onPressed: () {
          final input = _CredentialSubmission(
            _record.text.trim(),
            _secret.text.trim(),
          );
          _secret.clear();
          Navigator.pop(context, input);
        },
        child: const Text('Claim'),
      ),
    ],
  );
}

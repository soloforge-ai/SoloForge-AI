import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../services/soloforge_session_service.dart';
import '../services/pollinations_session_service.dart';

/// Read-only owner inspection; never handles the stored provider SK.
class PollinationsAccountInspectPage extends StatefulWidget {
  const PollinationsAccountInspectPage({super.key});

  @override
  State<PollinationsAccountInspectPage> createState() =>
      _PollinationsAccountInspectPageState();
}

class _PollinationsAccountInspectPageState
    extends State<PollinationsAccountInspectPage> {
  final _sessions = SoloForgeSessionService();
  final _client = http.Client();
  List<Map<String, dynamic>> _choices = [];
  String? _selected;
  Map<String, dynamic>? _result;
  String? _error;
  bool _busy = false;

  String get _base => assetForgeApiUrl.replaceFirst(RegExp(r'/$'), '');

  @override
  void initState() {
    super.initState();
    _loadChoices();
  }

  Future<void> _loadChoices() async {
    setState(() { _busy = true; _error = null; });
    try {
      final headers = await _sessions.authorizationHeaders();
      final response = await _client.get(
        Uri.parse('$_base/auth/pollinations/account/credentials'),
        headers: headers,
      ).timeout(const Duration(seconds: 20));
      if (response.statusCode != 200) {
        throw Exception('Could not load stored credentials (HTTP ${response.statusCode}).');
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

  Future<void> _inspect() async {
    final id = _selected;
    if (id == null || _busy) return;
    setState(() { _busy = true; _error = null; _result = null; });
    try {
      final headers = await _sessions.authorizationHeaders();
      final uri = Uri.parse('$_base/auth/pollinations/account/inspect')
          .replace(queryParameters: {'credential_record_id': id});
      final response = await _client.get(uri, headers: headers)
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
    body: ListView(padding: const EdgeInsets.all(20), children: [
      const Text('Read-only account evidence. No new key, spending, or owner binding.'),
      const SizedBox(height: 16),
      if (_busy) const LinearProgressIndicator(),
      if (_choices.isEmpty)
        const Text('No active stored credentials loaded.'),
      if (_choices.isNotEmpty)
        DropdownButtonFormField<String>(
          value: _selected,
          decoration: const InputDecoration(labelText: 'Existing credential record'),
          items: _choices.map((row) {
            final id = row['id']?.toString() ?? '';
            return DropdownMenuItem(
              value: id,
              child: Text('${id.substring(0, id.length < 8 ? id.length : 8)}…  ${row['scope'] ?? ''}'),
            );
          }).toList(),
          onChanged: _busy ? null : (value) => setState(() => _selected = value),
        ),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: _busy || _selected == null ? null : _inspect,
        child: const Text('Inspect existing account'),
      ),
      if (_error != null) Text(_error!, style: const TextStyle(color: Colors.redAccent)),
      if (_result != null) ...[
        const SizedBox(height: 16),
        Text('State: ${_result!['state'] ?? 'UNKNOWN'}'),
        Text('Provider subject: ${_result!['provider_subject'] ?? 'Unavailable'}'),
        Text('Owner binding: ${_result!['owner_binding'] ?? 'UNVERIFIED'}'),
        Text('Spending authorized: ${_result!['spending_authorized'] == true ? 'Yes' : 'No'}'),
        const SizedBox(height: 12),
        for (final name in ['identity', 'key', 'balance', 'usage'])
          ListTile(
            title: Text(name),
            subtitle: Text(jsonEncode((_result!['evidence'] as Map?)?[name] ?? {})),
          ),
      ],
    ]),
  );
}

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../services/owner_v2_session_service.dart';
import '../services/pollinations_session_service.dart';

/// Read-only diagnostic; never claims a credential or authorizes spending.
class PollinationsSkDiagnosticPage extends StatefulWidget {
  const PollinationsSkDiagnosticPage({super.key});

  @override
  State<PollinationsSkDiagnosticPage> createState() => _PollinationsSkDiagnosticPageState();
}

class _PollinationsSkDiagnosticPageState extends State<PollinationsSkDiagnosticPage> {
  final _recordId = TextEditingController();
  bool _busy = false;
  String? _result;
  String? _error;

  Future<void> _check() async {
    if (_busy) return;
    final id = _recordId.text.trim();
    if (!RegExp(r'^[0-9a-fA-F-]{36}$').hasMatch(id)) {
      setState(() => _error = 'Enter a valid credential record ID.');
      return;
    }
    setState(() { _busy = true; _error = null; _result = null; });
    try {
      final headers = await OwnerV2SessionService.shared.authorizationHeaders();
      final uri = Uri.parse('${assetForgeApiUrl.replaceFirst(RegExp(r"/$"), "")}/auth/pollinations/sk/identity-diagnostic')
          .replace(queryParameters: {'credential_record_id': id});
      final response = await http.get(uri, headers: headers).timeout(const Duration(seconds: 20));
      if (response.statusCode == 401 || response.statusCode == 403) {
        throw const FormatException('Owner session is not authorized.');
      }
      if (response.statusCode == 404) {
        throw const FormatException('Credential is not bound to this owner.');
      }
      if (response.statusCode != 200) {
        throw const FormatException('Diagnostic unavailable. Check backend deployment.');
      }
      final decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) throw const FormatException('Invalid response.');
      final comparison = decoded['comparison'];
      if (!['MATCH', 'MISMATCH', 'UNKNOWN'].contains(comparison) ||
          decoded['spending_authorized'] != false) {
        throw const FormatException('Unexpected diagnostic response.');
      }
      if (mounted) {
        setState(() {
          _result = '$comparison — ${decoded['reason'] ?? 'Comparison only; not proof of ownership'}';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _error = e is FormatException ? e.message : 'Unable to complete check. Please retry later.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _recordId.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Pollinations SK check')),
    body: Center(child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 520),
      child: ListView(shrinkWrap: true, padding: const EdgeInsets.all(20), children: [
        const Text('Check an existing owner-bound SK using its credential record ID. Never paste your secret key here.'),
        const SizedBox(height: 16),
        TextField(controller: _recordId, decoration: const InputDecoration(labelText: 'Credential record ID')),
        const SizedBox(height: 12),
        FilledButton(onPressed: _busy ? null : _check, child: Text(_busy ? 'Checking…' : 'Check identity')),
        if (_result != null) SelectableText(_result!),
        if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        const SizedBox(height: 12),
        const Text('MATCH compares provider userinfo with a configured reference; it does not verify owner binding or authorize spending.'),
      ]),
    )),
  );
}

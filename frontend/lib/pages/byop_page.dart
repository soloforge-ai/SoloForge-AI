import 'dart:async';
import 'dart:typed_data';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import '../services/byop_service.dart';

/// Minimal bounded BYOP journey; it never changes owner administration access.
class ByopPage extends StatefulWidget {
  const ByopPage({super.key, required this.member});
  final bool member;
  @override
  State<ByopPage> createState() => _ByopPageState();
}

class _ByopPageState extends State<ByopPage> {
  late final ByopService _service;
  final _key = TextEditingController();
  final _script = TextEditingController(text: 'Welcome to SoloForge.');
  final _maximum = TextEditingController();
  final _jobId = TextEditingController();
  StreamSubscription<AuthState>? _authChanges;
  String? _userId;
  String? _principal;
  String? _consent;
  String? _consentCredential;
  String? _execution;
  String? _notice;
  Map<String, dynamic>? _job;
  Map<String, dynamic>? _credential;
  List<Map<String, dynamic>> _credentials = [];
  Uint8List? _image;
  bool _displayed = false;
  bool _busy = false;
  bool _confirmed = false;
  bool _attempted = false;

  @override
  void initState() {
    super.initState();
    _service = ByopService(member: widget.member);
    _userId = Supabase.instance.client.auth.currentUser?.id;
    _authChanges = Supabase.instance.client.auth.onAuthStateChange.listen((_) {
      final current = Supabase.instance.client.auth.currentUser?.id;
      if (current != _userId && mounted) {
        setState(() {
          _userId = current; _principal = null; _image = null; _displayed = false;
          _job = null; _credential = null; _consent = null; _execution = null;
          _consentCredential = null; _credentials = []; _key.clear(); _jobId.clear(); _script.clear();
          _notice = 'Account changed. Reopen BYOP to validate access.';
        });
      }
    });
    _run(_connectApplication);
  }

  Future<void> _run(Future<void> Function() action) async {
    if (_busy) return;
    setState(() { _busy = true; _notice = null; });
    try { await action(); }
    catch (error) { if (mounted) setState(() => _notice = error.toString()); }
    finally { if (mounted) setState(() => _busy = false); }
  }

  Future<void> _connectApplication() async {
    await _service.headers();
    final principal = _service.principal!;
    final status = await _service.connections.byopStatus(principal);
    final list = await _service.get('credentials');
    if (mounted) setState(() {
      if (_credential?['credential_id'] != status['credential_id']) {
        _consent = null; _consentCredential = null; _execution = null; _confirmed = false;
      }
      _principal = principal; _credential = status;
      _credentials = (list['credentials'] as List).cast<Map<String, dynamic>>(); });
  }

  Future<void> _loadJob() async {
    final job = await _service.get('jobs/${_jobId.text.trim()}');
    final package = job['content_package'] as Map<String, dynamic>;
    Uint8List? image;
    if (package['asset_sha256'] != null) {
      image = await _service.image(job['id'] as String, package['asset_sha256'] as String);
    }
    if (mounted) setState(() { _job = job; _image = image; _displayed = false; });
  }

  int _maximumMicroPollen() {
    final value = _maximum.text.trim();
    if (!RegExp(r'^\d+(\.\d{1,6})?$').hasMatch(value)) {
      throw const FormatException('Enter a positive Pollen maximum with at most six decimals.');
    }
    final parts = value.split('.');
    final amount = int.parse(parts[0]) * 1000000 +
        (parts.length == 2 ? int.parse(parts[1].padRight(6, '0')) : 0);
    if (amount <= 0) throw const FormatException('Maximum must be positive.');
    return amount;
  }

  @override
  void dispose() {
    _authChanges?.cancel();
    _key.clear(); _key.dispose(); _script.dispose(); _maximum.dispose(); _jobId.dispose();
    _service.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final jobId = _job?['id'] as String?;
    final status = _job?['status'];
    return Scaffold(
      appBar: AppBar(title: Text(widget.member ? 'Member BYOP' : 'Owner BYOP')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        const Text('Use your own Pollinations account. Connecting never authorizes Pollen spending.'),
        const SizedBox(height: 12),
        Text(_principal == null ? 'Application access not verified. Sign in using the existing GitHub flow first.' : 'Authenticated: $_principal'),
        OutlinedButton(onPressed: _busy ? null : () => _run(_connectApplication), child: const Text('Verify application access')),
        if (_principal != null) ...[
          Text('Selected credential: ${_credential?['credential_id'] ?? 'none'}\nStatus: ${_credential?['verification_status'] ?? 'not connected'}'),
          for (final choice in _credentials)
            OutlinedButton(onPressed: _busy || choice['disconnected'] == true ? null : () => _run(() async {
              await _service.connections.selectByopCredential(_principal!, choice['credential_id'] as String);
              await _connectApplication();
            }), child: Text('Select ${choice['credential_id']} (${choice['verification_status']})')),
          TextField(controller: _key, obscureText: true, enableSuggestions: false, autocorrect: false,
              decoration: const InputDecoration(labelText: 'Your Pollinations SK')),
          FilledButton(onPressed: _busy ? null : () => _run(() async {
            await _service.connections.submitByopKey(_principal!, _key.text.trim());
            _key.clear(); await _connectApplication();
          }), child: const Text('Connect as pending')),
          OutlinedButton(onPressed: _busy ? null : () => _run(() async {
            await _service.connections.verifyByopCredential(_principal!); await _connectApplication();
          }), child: const Text('Verify credential ownership')),
          OutlinedButton(onPressed: _busy ? null : () => _run(() async {
            await _service.connections.disconnectByop(_principal!); await _connectApplication();
            if (mounted) setState(() => _notice = 'Server authorization disconnected. Already claimed executions may complete. Upstream key revocation is not confirmed.');
          }), child: const Text('Disconnect')),
          const Divider(),
          const Text('One CEO image • presenting • calm • kontext • 1024×1024'),
          TextField(controller: _script, maxLines: 3, decoration: const InputDecoration(labelText: 'Your narration/subtitle script')),
          FilledButton(onPressed: _busy ? null : () => _run(() async {
            final job = await _service.post('jobs', {'asset_forge_request': {
              'character': 'CEO', 'generation_layout': 'single_character', 'quantity': 1,
              'pose_intent': 'presenting', 'expression': 'calm'}, 'script': _script.text});
            _jobId.text = job['id'] as String;
            if (mounted) setState(() { _consent = null; _consentCredential = null; _execution = null; _attempted = false; _confirmed = false; });
            await _loadJob();
          }), child: const Text('Create CEO Content Job')),
          TextField(controller: _jobId, decoration: const InputDecoration(labelText: 'Content Job ID (save for recovery)')),
          OutlinedButton(onPressed: _busy ? null : () => _run(_loadJob), child: const Text('Load / refresh my job')),
          if (jobId != null) ...[
            SelectableText('Job: $jobId\nStatus: $status'),
            OutlinedButton(onPressed: _busy ? null : () => _run(() async {
              final result = await _service.get('jobs/$jobId/executions');
              if (mounted) setState(() => _notice = 'Execution history: ${result['executions']}. Unknown charges require reconciliation.');
            }), child: const Text('Check execution / reconciliation state')),
            TextField(controller: _maximum, keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Maximum Pollen for this one execution')),
            const Text('A trusted server estimate is required. Spending stays blocked when pricing is unavailable.'),
            CheckboxListTile(value: _confirmed, onChanged: _busy ? null : (v) => setState(() => _confirmed = v ?? false),
                title: const Text('Authorize only this job, my selected credential and maximum, expiring in five minutes.')),
            FilledButton(onPressed: _busy || !_confirmed || _credential?['verification_status'] != 'VERIFIED' ? null : () => _run(() async {
              final id = await _service.connections.byopCredentialId(_principal!);
              if (id == null) throw const FormatException('Connect your own credential first.');
              final result = await _service.post('jobs/$jobId/consents', {'credential_id': id,
                'maximum_micro_pollen': _maximumMicroPollen(),
                'expires_at': DateTime.now().millisecondsSinceEpoch / 1000 + 300});
              if (mounted) setState(() { _consent = result['consent_id'] as String; _consentCredential = id; _execution = ByopService.newExecutionId(); });
            }), child: const Text('Authorize bounded spending')),
            if (_execution != null) SelectableText('Execution: $_execution'),
            FilledButton(onPressed: _busy || _consent == null || _attempted ? null : () => _run(() async {
              if (await _service.connections.byopCredentialId(_principal!) != _consentCredential) {
                throw const FormatException('Selected credential changed. Refresh and authorize again.');
              }
              setState(() => _attempted = true);
              await _service.post('executions', {'consent_id': _consent, 'execution_id': _execution});
              await _loadJob();
            }), child: const Text('Generate once')),
            if (_attempted) const Text('Execution submitted. Unknown outcomes require reconciliation; do not automatically retry.'),
            if (_image != null) Image.memory(_image!, frameBuilder: (context, child, frame, syncLoaded) {
              final displayed = _image;
              if (frame != null && !_displayed) {
                WidgetsBinding.instance.addPostFrameCallback((_) {
                  if (mounted && identical(displayed, _image)) setState(() => _displayed = true);
                });
              }
              return child;
            }, errorBuilder: (_, __, ___) => const Text('Image could not be displayed.')),
            for (final approved in [true, false]) OutlinedButton(
              onPressed: _busy || !_displayed || status != 'READY_FOR_REVIEW' ? null : () => _run(() async {
                await _service.review(jobId, _image!, approved); await _loadJob();
              }), child: Text(approved ? 'Approve displayed image' : 'Reject displayed image')),
            OutlinedButton(onPressed: _busy || status != 'ASSET_READY' ? null : () => _run(() async {
              final pick = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['wav'], withData: true);
              if (pick == null) return;
              final wav = pick.files.single.bytes;
              if (wav == null || wav.length > 8 * 1024 * 1024) throw const FormatException('Choose a PCM WAV of at most 8 MiB and 60 seconds.');
              await _service.audio(jobId, wav); await _loadJob();
            }), child: const Text('Attach my narration WAV')),
            FilledButton(onPressed: _busy || status != 'AUDIO_READY' ? null : () => _run(() async {
              await _service.post('jobs/$jobId/render', {}); await _loadJob();
            }), child: const Text('Render approved image')),
            OutlinedButton(onPressed: _busy || status != 'READY_TO_PUBLISH' ? null : () => _run(() async {
              final result = await _service.get('jobs/$jobId/video');
              await launchUrl(Uri.parse(result['url'] as String), mode: LaunchMode.externalApplication);
            }), child: const Text('Preview my render')),
          ],
        ],
        if (_busy) const LinearProgressIndicator(),
        if (_notice != null) Padding(padding: const EdgeInsets.only(top: 16), child: Text(_notice!)),
        const SizedBox(height: 16),
        const Text('Publishing and background workers remain disabled.'),
      ]),
    );
  }
}

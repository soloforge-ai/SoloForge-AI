import 'dart:async';
import 'dart:typed_data';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:share_plus/share_plus.dart';
import 'package:crypto/crypto.dart';
import '../services/byop_service.dart';

/// Minimal bounded BYOP journey; it never changes owner administration access.
class ByopPage extends StatefulWidget {
  const ByopPage({super.key, required this.member, this.service});
  final bool member;
  final ByopService? service;
  @override
  State<ByopPage> createState() => _ByopPageState();
}

class _ByopPageState extends State<ByopPage> {
  late final ByopService _service;
  final _key = TextEditingController();
  final _account = TextEditingController();
  String? _cfCredentialId;
  bool get _cloudflare => _service.provider == 'cloudflare';
  bool get _liveCloudflare => _cloudflare && _readiness['transport_mode'] == 'cloudflare_http';
  static const _cfModel = '@cf/black-forest-labs/flux-1-schnell';
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
  Map<String, dynamic>? _identityDiscovery;
  Map<String, dynamic>? _job;
  Map<String, dynamic>? _credential;
  Map<String, dynamic> _readiness = {};
  int? _quotedMaximum;
  List<Map<String, dynamic>> _credentials = [];
  Uint8List? _image;
  bool _displayed = false;
  bool _busy = false;
  bool _confirmed = false;
  bool _attempted = false;

  @override
  void initState() {
    super.initState();
    _service = widget.service ?? ByopService(member: widget.member);
    if (widget.service == null) {
    _userId = Supabase.instance.client.auth.currentUser?.id;
    _authChanges = Supabase.instance.client.auth.onAuthStateChange.listen((_) {
      final current = Supabase.instance.client.auth.currentUser?.id;
      if (current != _userId && mounted) {
        setState(() {
          _userId = current; _principal = null; _image = null; _displayed = false;
          _job = null; _credential = null; _consent = null; _execution = null;
          _cfCredentialId = null; _account.clear();
          _readiness = {}; _quotedMaximum = null;
          _consentCredential = null; _credentials = []; _key.clear(); _jobId.clear(); _script.clear();
          _notice = 'Account changed. Reopen BYOP to validate access.';
        });
      }
    });
    }
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
    final status = _cloudflare
        ? (_cfCredentialId == null ? <String, dynamic>{'connected': false} : await _service.get('credentials/$_cfCredentialId'))
        : await _service.connections.byopStatus(principal);
    final list = await _service.get('credentials');
    if (mounted) {
      setState(() {
        if (_credential?['credential_id'] != status['credential_id']) {
          _consent = null; _consentCredential = null; _execution = null; _confirmed = false;
        }
        _principal = principal; _credential = status;
        _readiness = _service.readiness;
        _credentials = (list['credentials'] as List).cast<Map<String, dynamic>>();
      });
    }
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

  Future<void> _changeProvider(String value) async {
    if (value == _service.provider) return;
    _service.provider = value;
    setState(() {
      _credential = null; _identityDiscovery = null; _cfCredentialId = null; _job = null; _image = null;
      _consent = null; _consentCredential = null; _execution = null; _quotedMaximum = null;
      _confirmed = false; _attempted = false; _displayed = false; _key.clear(); _jobId.clear();
    });
    await _connectApplication();
  }

  int _maximumMicroPollen() {
    if (_cloudflare) {
      final amount = int.tryParse(_maximum.text.trim());
      if (amount == null || amount <= 0) throw const FormatException('Enter a positive integer Neurons maximum.');
      return amount;
    }
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
    _account.clear(); _account.dispose();
    _key.clear(); _key.dispose(); _script.dispose(); _maximum.dispose(); _jobId.dispose();
    _service.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final jobId = _job?['id'] as String?;
    final status = _job?['status'];
    final pilotEligible = _readiness['pilot_role_eligible'] == true;
    return Scaffold(
      appBar: AppBar(title: Text(widget.member ? 'Member BYOP' : 'Owner BYOP')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        DropdownButtonFormField<String>(
          initialValue: _service.provider,
          decoration: const InputDecoration(labelText: 'Image provider'),
          items: [
            const DropdownMenuItem(value: 'pollinations', child: Text('Pollinations')),
            DropdownMenuItem(value: 'cloudflare', enabled: !widget.member && _service.cloudflareAvailable,
              child: const Text('Cloudflare — server capability required')),
          ],
          onChanged: _busy ? null : (value) { if (value != null) _run(() => _changeProvider(value)); },
        ),
        Text(_cloudflare ? (_liveCloudflare
          ? 'Cloudflare text-to-image. No image-to-image or CEO identity guarantee.'
          : 'Mock images only. Not CEO identity compatible. No live provider execution.')
          : 'Use your own Pollinations account. Connecting never authorizes Pollen spending.'),
        const SizedBox(height: 12),
        Text(_principal == null ? 'Application access not verified. Sign in using the existing GitHub flow first.' : 'Authenticated: $_principal'),
        OutlinedButton(onPressed: _busy ? null : () => _run(_connectApplication), child: const Text('Verify application access')),
        if (_principal != null) ...[
          Text(_readiness['reason']?.toString() ?? 'Generation readiness unavailable; spending remains locked.'),
          Text(_liveCloudflare ? 'Live transport configured. Verified credentials, trusted pricing, Neurons budget and explicit consent are mandatory.'
            : 'Live generation remains locked. Owner pilot eligibility is not spending permission.'),
          if (!_cloudflare) ...[
          Text('Developer earnings: ${(_readiness['earnings'] as Map?)?['status'] ?? 'unverified'}. No earnings confirmed.'),
          const Text('Existing SKs do not prove App Key attribution. Eligible App Key traffic adds 25% to base usage; app-owner self-use is excluded.'),
          const Text('Total cost: unavailable until a trusted server quote, including any applicable markup. No request will run without bounded consent.'),
          const Text('For insufficient provider balance or key budget, use Pollinations’ official Quests dashboard. Rewards and eligibility are not guaranteed; a started call will not be retried.'),
          const SelectableText('https://enter.pollinations.ai/quests'),
          ],
          Text('Selected credential: ${_credential?['credential_id'] ?? 'none'}\nStatus: ${_credential?['verification_status'] ?? 'not connected'}'),
          for (final choice in _credentials)
            OutlinedButton(onPressed: _busy || choice['disconnected'] == true ? null : () => _run(() async {
              if (_cloudflare) {
                _cfCredentialId = choice['credential_id'] as String;
              } else {
                await _service.connections.selectByopCredential(_principal!, choice['credential_id'] as String);
              }
              await _connectApplication();
            }), child: Text('Select ${choice['credential_id']} (${choice['verification_status']})')),
          if (_cloudflare) TextField(controller: _account, decoration: const InputDecoration(labelText: 'Your Cloudflare Account ID')),
          TextField(controller: _key, obscureText: true, enableSuggestions: false, autocorrect: false,
              decoration: InputDecoration(labelText: _cloudflare ? 'Your Cloudflare API token' : 'Your Pollinations SK')),
          FilledButton(onPressed: _busy ? null : () => _run(() async {
            if (_cloudflare) {
              final result = await _service.post('credentials', {'access_token': _key.text.trim(), 'account_id': _account.text.trim()});
              _cfCredentialId = result['credential_id'] as String;
            } else {
              await _service.connections.submitByopKey(_principal!, _key.text.trim());
            }
            _key.clear(); await _connectApplication();
          }), child: const Text('Connect as pending')),
          if (!_cloudflare && !widget.member) ...[
            OutlinedButton(onPressed: _busy || _credential?['credential_id'] == null ? null : () => _run(() async {
              final result = await _service.connections.discoverByopIdentity(_principal!);
              if (mounted) setState(() => _identityDiscovery = result);
            }), child: const Text('Inspect SK identity (read-only)')),
            if (_identityDiscovery != null) Text(
              'Provider identity: ${_identityDiscovery!['identity_discovered'] == true ? 'DISCOVERED' : 'UNAVAILABLE'}'
              '\\nReason: ${_identityDiscovery!['reason']}'
              '\\nOwner binding: UNVERIFIED — no spending permission'),
          ],
          if (!_cloudflare) OutlinedButton(onPressed: _busy ? null : () => _run(() async {
            await _service.connections.verifyByopCredential(_principal!); await _connectApplication();
          }), child: const Text('Verify credential ownership')),
          OutlinedButton(onPressed: _busy ? null : () => _run(() async {
            if (_cloudflare) {
              if (_cfCredentialId != null) await _service.post('credentials/$_cfCredentialId/disconnect', {});
              _cfCredentialId = null;
            } else {
              await _service.connections.disconnectByop(_principal!);
            }
            await _connectApplication();
            if (mounted) setState(() => _notice = 'Server authorization disconnected. Already claimed executions may complete. Upstream key revocation is not confirmed.');
          }), child: const Text('Disconnect')),
          const Divider(),
          Text(_cloudflare ? 'One text-to-image mock • no reference identity guarantee' : 'One CEO image • presenting • calm • kontext • 1024×1024'),
          if (_cloudflare) DropdownButtonFormField<String>(initialValue: _cfModel,
            decoration: const InputDecoration(labelText: 'Image model'),
            items: const [DropdownMenuItem(value: _cfModel, child: Text('FLUX.1 Schnell'))],
            onChanged: _busy ? null : (_) {}),
          TextField(controller: _script, maxLines: 3, decoration: InputDecoration(labelText: _cloudflare ? 'Your image prompt' : 'Your narration/subtitle script')),
          FilledButton(onPressed: _busy ? null : () => _run(() async {
            final job = await _service.post('jobs', {'asset_forge_request': _cloudflare ? {'prompt': _script.text, 'model': _cfModel} : {
              'character': 'CEO', 'generation_layout': 'single_character', 'quantity': 1,
              'pose_intent': 'presenting', 'expression': 'calm'}, 'script': _script.text});
            _jobId.text = job['id'] as String;
            if (mounted) setState(() { _consent = null; _consentCredential = null; _execution = null; _attempted = false; _confirmed = false; });
            await _loadJob();
          }), child: Text(_cloudflare ? (_liveCloudflare ? 'Create Cloudflare image job' : 'Create mock image job') : 'Create CEO Content Job')),
          TextField(controller: _jobId, decoration: const InputDecoration(labelText: 'Content Job ID (save for recovery)')),
          OutlinedButton(onPressed: _busy ? null : () => _run(_loadJob), child: const Text('Load / refresh my job')),
          if (jobId != null) ...[
            SelectableText('Job: $jobId\nStatus: $status'),
            OutlinedButton(onPressed: _busy ? null : () => _run(() async {
              final result = await _service.get('jobs/$jobId/executions');
              if (mounted) setState(() => _notice = 'Execution history: ${result['executions']}. Unknown charges require reconciliation.');
            }), child: const Text('Check execution / reconciliation state')),
            TextField(controller: _maximum, keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: InputDecoration(labelText: _cloudflare ? (_liveCloudflare ? 'Maximum Neurons for this execution' : 'Maximum Neurons for this mock execution') : 'Maximum Pollen for this one execution')),
            const Text('A trusted server estimate is required. Spending stays blocked when pricing is unavailable.'),
            CheckboxListTile(value: _confirmed, onChanged: _busy ? null : (v) => setState(() => _confirmed = v ?? false),
                title: const Text('Authorize only this job, my selected credential and maximum, expiring in five minutes.')),
            FilledButton(onPressed: _busy || !pilotEligible || !_confirmed || _credential?['verification_status'] != 'VERIFIED' ? null : () => _run(() async {
              final id = _cloudflare ? _cfCredentialId : await _service.connections.byopCredentialId(_principal!);
              if (id == null) throw const FormatException('Connect your own credential first.');
              final result = await _service.post('jobs/$jobId/consents', {'credential_id': id,
                (_cloudflare ? 'maximum_neurons' : 'maximum_micro_pollen'): _maximumMicroPollen(),
                'expires_at': DateTime.now().millisecondsSinceEpoch / 1000 + 300});
              if (mounted) {
                setState(() {
                  _consent = result['consent_id'] as String; _consentCredential = id; _execution = ByopService.newExecutionId();
                  _quotedMaximum = (result['quote'] as Map<String, dynamic>)[_cloudflare ? 'maximum_neurons' : 'maximum_micro_pollen'] as int;
                });
              }
            }), child: Text(_cloudflare ? (_liveCloudflare ? 'Authorize bounded Cloudflare execution' : 'Authorize bounded mock execution') : 'Authorize bounded spending')),
            if (_consent != null && _quotedMaximum != null)
              Text(_cloudflare ? (_liveCloudflare ? 'Server-quoted maximum: $_quotedMaximum Neurons; final charge unknown until reconciled.' : 'Server-quoted mock maximum: $_quotedMaximum Neurons; not a provider charge.') : 'Server-quoted maximum total: ${(_quotedMaximum! / 1000000).toStringAsFixed(6)} Pollen. This is a bound, not a confirmed charge or earnings.'),
            if (_execution != null) SelectableText('Execution: $_execution'),
            FilledButton(onPressed: _busy || !pilotEligible || _consent == null || _attempted ? null : () => _run(() async {
              if ((_cloudflare ? _cfCredentialId : await _service.connections.byopCredentialId(_principal!)) != _consentCredential) {
                throw const FormatException('Selected credential changed. Refresh and authorize again.');
              }
              setState(() => _attempted = true);
              await _service.post('executions', {'consent_id': _consent, 'execution_id': _execution});
              await _loadJob();
            }), child: Text(_cloudflare ? (_liveCloudflare ? 'Generate Cloudflare image once' : 'Generate mock image once') : 'Generate once')),
            if (_attempted) const Text('Execution submitted. Unknown outcomes require reconciliation; do not automatically retry.'),
            if (_image != null) Image.memory(_image!, frameBuilder: (context, child, frame, syncLoaded) {
              final displayed = _image;
              if (frame != null && !_displayed) {
                WidgetsBinding.instance.addPostFrameCallback((_) {
                  if (mounted && identical(displayed, _image)) setState(() => _displayed = true);
                });
              }
              return child;
            }, errorBuilder: (context, error, stackTrace) => const Text('Image could not be displayed.')),
            for (final approved in [true, false]) OutlinedButton(
              onPressed: _busy || !_displayed || status != 'READY_FOR_REVIEW' ? null : () => _run(() async {
                await _service.review(jobId, _image!, approved); await _loadJob();
              }), child: Text(approved ? 'Approve displayed image' : 'Reject displayed image')),
            if (_cloudflare) for (final zip in [false, true]) OutlinedButton(
              onPressed: _busy || status != 'ASSET_READY' || _image == null ? null : () => _run(() async {
                final sha = sha256.convert(_image!).toString();
                final bytes = await _service.exportAsset(jobId, sha, zip: zip);
                final name = 'soloforge-$jobId.${zip ? 'zip' : 'png'}';
                await SharePlus.instance.share(ShareParams(
                  files: [XFile.fromData(bytes, mimeType: zip ? 'application/zip' : 'image/png', name: name)],
                  fileNameOverrides: [name]));
              }), child: Text(zip ? 'Export approved ZIP' : 'Export approved PNG')),
            OutlinedButton(onPressed: _busy || _cloudflare || status != 'ASSET_READY' ? null : () => _run(() async {
              final pick = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['wav'], withData: true);
              if (pick == null) return;
              final wav = pick.files.single.bytes;
              if (wav == null || wav.length > 8 * 1024 * 1024) throw const FormatException('Choose a PCM WAV of at most 8 MiB and 60 seconds.');
              await _service.audio(jobId, wav); await _loadJob();
            }), child: const Text('Attach my narration WAV')),
            FilledButton(onPressed: _busy || _cloudflare || status != 'AUDIO_READY' ? null : () => _run(() async {
              await _service.post('jobs/$jobId/render', {}); await _loadJob();
            }), child: const Text('Render approved image')),
            OutlinedButton(onPressed: _busy || _cloudflare || status != 'READY_TO_PUBLISH' ? null : () => _run(() async {
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

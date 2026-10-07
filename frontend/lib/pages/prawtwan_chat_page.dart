import 'dart:async';

import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import '../services/prawtwan_chat_service.dart';
import '../services/prawtwan_language.dart';
import '../services/pollinations_session_service.dart';

class PrawtwanChatPage extends StatefulWidget {
  const PrawtwanChatPage({super.key, this.service});

  final PrawtwanChatService? service;

  @override
  State<PrawtwanChatPage> createState() => _PrawtwanChatPageState();
}

class _PrawtwanChatPageState extends State<PrawtwanChatPage> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  late final PrawtwanChatService _service =
      widget.service ?? PrawtwanChatService();
  final PrawtwanLanguagePreference _preference = PrawtwanLanguagePreference();
  PrawtwanCopy? _copy;
  bool _languageChanged = false;
  Future<void> _pendingSave = Future.value();
  final List<PrawtwanMessage> _messages = [];
  bool _sending = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_copy != null) return;
    _copy = PrawtwanCopy.forLocale(
      WidgetsBinding.instance.platformDispatcher.locale,
    );
    unawaited(_restoreLanguage());
  }

  Future<void> _restoreLanguage() async {
    final saved = await _preference.read();
    if (mounted && !_languageChanged && saved != null) {
      setState(() => _copy = PrawtwanCopy(saved));
    }
  }

  void _selectLanguage(String? code) {
    if (code == null) return;
    _languageChanged = true;
    setState(() => _copy = PrawtwanCopy(code));
    _pendingSave = _pendingSave.then((_) async {
      final saved = await _preference.write(code);
      if (!saved && mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(_copy!.saveError)));
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    unawaited(_service.dispose());
    super.dispose();
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _sending) return;

    _controller.clear();
    setState(() {
      _messages.add(PrawtwanMessage(role: 'user', content: text));
      _sending = true;
    });
    _scrollToBottom();

    try {
      final reply = await _service.send(List<PrawtwanMessage>.from(_messages));
      if (!mounted) return;
      setState(() {
        _messages.add(PrawtwanMessage(role: 'assistant', content: reply));
      });
      _scrollToBottom();
    } on PrawtwanChatException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(_copy!.error(error.message))));
    } on PollinationsSessionException {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(_copy!.connect)));
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(_copy!.unavailable)));
    } finally {
      if (mounted) {
        setState(() => _sending = false);
        _scrollToBottom();
      }
    }
  }

  void _clearChat() {
    if (_messages.isEmpty || _sending) return;
    setState(_messages.clear);
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final copy = _copy!;
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              copy.title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 17),
            ),
            Text(
              copy.subtitle,
              style: const TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w500,
                color: AshColors.smokeSilver,
              ),
            ),
          ],
        ),
        actions: [
          DropdownButton<String>(
            value: copy.code,
            onChanged: _selectLanguage,
            items: const [
              DropdownMenuItem(value: 'th', child: Text('ไทย')),
              DropdownMenuItem(value: 'en', child: Text('English')),
            ],
          ),
          IconButton(
            tooltip: copy.clear,
            onPressed: _messages.isEmpty || _sending ? null : _clearChat,
            icon: const Icon(Icons.delete_outline),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Container(
              width: double.infinity,
              margin: const EdgeInsets.fromLTRB(12, 4, 12, 8),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AshColors.blackPlum,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: AshColors.indigoMist.withValues(alpha: 0.45),
                ),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.lock_outline,
                    size: 15,
                    color: AshColors.indigoMist,
                  ),
                  const SizedBox(width: 7),
                  Expanded(
                    child: Text(
                      copy.privacy,
                      style: const TextStyle(
                        fontSize: 10,
                        color: AshColors.smokeSilver,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: _messages.isEmpty && !_sending
                  ? _EmptyChat(copy: copy)
                  : ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.fromLTRB(12, 6, 12, 12),
                      itemCount: _messages.length + (_sending ? 1 : 0),
                      itemBuilder: (context, index) {
                        if (index == _messages.length) {
                          return _ThinkingBubble(copy: copy);
                        }
                        return _MessageBubble(
                          message: _messages[index],
                          copy: copy,
                        );
                      },
                    ),
            ),
            Container(
              padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
              decoration: BoxDecoration(
                color: AshColors.obsidian,
                border: Border(
                  top: BorderSide(
                    color: AshColors.indigoMist.withValues(alpha: 0.22),
                  ),
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      minLines: 1,
                      maxLines: 6,
                      enabled: !_sending,
                      textInputAction: TextInputAction.newline,
                      decoration: InputDecoration(
                        hintText: copy.hint,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  SizedBox(
                    width: 46,
                    height: 46,
                    child: Tooltip(
                      message: copy.send,
                      child: FilledButton(
                        onPressed: _sending ? null : _send,
                        style: FilledButton.styleFrom(
                          padding: EdgeInsets.zero,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: _sending
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.arrow_upward_rounded),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyChat extends StatelessWidget {
  const _EmptyChat({required this.copy});
  final PrawtwanCopy copy;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: AshColors.blackPlum,
                shape: BoxShape.circle,
                border: Border.all(color: AshColors.indigoMist),
              ),
              child: const Icon(
                Icons.auto_stories_outlined,
                size: 30,
                color: AshColors.boneWhite,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              copy.emptyTitle,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w800,
                color: AshColors.boneWhite,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              copy.emptyBody,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 12,
                height: 1.45,
                color: AshColors.smokeSilver,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message, required this.copy});
  final PrawtwanCopy copy;

  final PrawtwanMessage message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == 'user';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 620),
        margin: EdgeInsets.only(
          left: isUser ? 42 : 0,
          right: isUser ? 0 : 42,
          bottom: 10,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: isUser ? AshColors.deepIndigo : AshColors.charcoal,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isUser
                ? AshColors.indigoMist.withValues(alpha: 0.55)
                : AshColors.mutedRose.withValues(alpha: 0.45),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              isUser ? copy.you : copy.name,
              style: const TextStyle(
                fontSize: 9,
                fontWeight: FontWeight.w800,
                color: AshColors.smokeSilver,
              ),
            ),
            const SizedBox(height: 4),
            SelectableText(
              message.content,
              style: const TextStyle(
                fontSize: 14,
                height: 1.45,
                color: AshColors.boneWhite,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ThinkingBubble extends StatelessWidget {
  const _ThinkingBubble({required this.copy});
  final PrawtwanCopy copy;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: 8),
            Text(
              copy.thinking,
              style: const TextStyle(
                fontSize: 11,
                color: AshColors.smokeSilver,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

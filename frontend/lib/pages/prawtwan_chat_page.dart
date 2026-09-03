import 'dart:async';

import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import '../services/prawtwan_chat_service.dart';

class PrawtwanChatPage extends StatefulWidget {
  const PrawtwanChatPage({super.key});

  @override
  State<PrawtwanChatPage> createState() => _PrawtwanChatPageState();
}

class _PrawtwanChatPageState extends State<PrawtwanChatPage> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final PrawtwanChatService _service = PrawtwanChatService();
  final List<PrawtwanMessage> _messages = [];

  bool _sending = false;

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
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Chat Prawtwan is temporarily unavailable.')),
      );
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
    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Chat Prawtwan'),
            Text(
              'PRAWTWAN — Fiction Editor',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w500,
                color: AshColors.smokeSilver,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Clear chat',
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
              child: const Row(
                children: [
                  Icon(Icons.lock_outline, size: 15, color: AshColors.indigoMist),
                  SizedBox(width: 7),
                  Expanded(
                    child: Text(
                      'Private agent • Session-only chat • Pollen is used only when you send',
                      style: TextStyle(
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
                  ? const _EmptyChat()
                  : ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.fromLTRB(12, 6, 12, 12),
                      itemCount: _messages.length + (_sending ? 1 : 0),
                      itemBuilder: (context, index) {
                        if (index == _messages.length) {
                          return const _ThinkingBubble();
                        }
                        return _MessageBubble(message: _messages[index]);
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
                      decoration: const InputDecoration(
                        hintText: 'พิมพ์ข้อความหรือวางฉากให้น้องพราวอ่าน...',
                        contentPadding: EdgeInsets.symmetric(
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
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.arrow_upward_rounded),
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
  const _EmptyChat();

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
            const Text(
              'พี่พราวพร้อมแล้ว',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w800,
                color: AshColors.boneWhite,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'ลองส่งฉาก บทสนทนา หรือคำถามเกี่ยวกับงานเขียนให้พี่พราวอ่านได้เลย',
              textAlign: TextAlign.center,
              style: TextStyle(
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
  const _MessageBubble({required this.message});

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
              isUser ? 'Ai' : 'Prawtwan',
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
  const _ThinkingBubble();

  @override
  Widget build(BuildContext context) {
    return const Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: EdgeInsets.only(bottom: 10),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            SizedBox(width: 8),
            Text(
              'พี่พราวกำลังอ่าน...',
              style: TextStyle(
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

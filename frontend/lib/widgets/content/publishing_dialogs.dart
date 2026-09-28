import 'package:flutter/material.dart';

import '../../models/content_job.dart';
import '../../services/content_job_service.dart';

class PublishingPlan {
  const PublishingPlan({
    required this.platformIds,
    this.scheduledTime,
  });

  final List<String> platformIds;
  final DateTime? scheduledTime;
}

Future<PublishingPlan?> choosePublishingPlan(
  BuildContext context, {
  required ContentJobService service,
  required ContentJob job,
  required bool schedule,
}) async {
  final connections = await service.getPublishingConnections();
  if (!context.mounted) return null;

  final active = connections
      .where((item) =>
          item.connectionStatus == 'active' &&
          (item.tokenStatus.isEmpty || item.tokenStatus == 'valid'))
      .toList();

  if (active.isEmpty) {
    throw Exception('No active Publora accounts are connected.');
  }

  final rawTargets = job.contentPackage['target_platforms'];
  final targets = rawTargets is List
      ? rawTargets.map((value) => value.toString().toLowerCase()).toSet()
      : <String>{};

  final selected = active
      .where((item) => targets.contains(item.platform.toLowerCase()))
      .map((item) => item.platformId)
      .toSet();

  final platformIds = await showDialog<List<String>>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (dialogContext, setDialogState) => AlertDialog(
        title: const Text('Choose publishing accounts'),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView(
            shrinkWrap: true,
            children: active.map((item) {
              final checked = selected.contains(item.platformId);
              return CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: checked,
                title: Text(item.platform.toUpperCase()),
                subtitle: Text(
                  item.username.isEmpty ? item.platformId : item.username,
                ),
                onChanged: (value) {
                  setDialogState(() {
                    if (value == true) {
                      selected.add(item.platformId);
                    } else {
                      selected.remove(item.platformId);
                    }
                  });
                },
              );
            }).toList(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: selected.isEmpty
                ? null
                : () => Navigator.pop(dialogContext, selected.toList()),
            child: const Text('Continue'),
          ),
        ],
      ),
    ),
  );

  if (platformIds == null || platformIds.isEmpty || !context.mounted) {
    return null;
  }

  if (!schedule) {
    return PublishingPlan(platformIds: platformIds);
  }

  final now = DateTime.now();
  final planned = job.plannedDate;
  final initialDate =
      planned != null && !planned.isBefore(DateTime(now.year, now.month, now.day))
          ? planned
          : now;

  final date = await showDatePicker(
    context: context,
    firstDate: DateTime(now.year, now.month, now.day),
    lastDate: now.add(const Duration(days: 365)),
    initialDate: initialDate,
  );
  if (date == null || !context.mounted) return null;

  final time = await showTimePicker(
    context: context,
    initialTime: const TimeOfDay(hour: 18, minute: 0),
  );
  if (time == null) return null;

  final scheduledTime = DateTime(
    date.year,
    date.month,
    date.day,
    time.hour,
    time.minute,
  );
  if (!scheduledTime.isAfter(DateTime.now())) {
    throw Exception('Scheduled time must be in the future.');
  }

  return PublishingPlan(
    platformIds: platformIds,
    scheduledTime: scheduledTime,
  );
}

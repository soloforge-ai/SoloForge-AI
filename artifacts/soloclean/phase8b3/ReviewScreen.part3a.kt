                    onClick = onClear,
                    modifier = Modifier.weight(1f),
                ) {
                    Text("CLEAR")
                }
            }
        }
    }
}

@Composable
private fun BatchResultCard(summary: CleanupSummary) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp)) {
            Text("Last cleanup batch", fontWeight = FontWeight.SemiBold)
            Text(
                "Success ${summary.successCount} · Skipped ${summary.skippedCount} · Failed ${summary.failedCount} · Permission ${summary.permissionRequiredCount}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (summary.reclaimedBytes > 0L) {
                Text(
                    "Reclaimed ${summary.reclaimedBytes.toReadableSize()}",
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}

@Composable
private fun DuplicateGroupCard(
    group: DuplicateReviewGroup,
    keeperUri: String,
    selectedUris: Set<String>,
    enabled: Boolean,
    onCheckedChange: (String, Boolean) -> Unit,
    onKeepThis: (String) -> Unit,
) {
    val selectedCount = group.members.count { it.uri in selectedUris }
    val selectedBytes = group.members.filter { it.uri in selectedUris }.sumOf { it.sizeBytes }

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp)) {
            Text("${group.members.size} identical files", fontWeight = FontWeight.SemiBold)
            Text(
                "$selectedCount selected · ${selectedBytes.toReadableSize()} selected for cleanup",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(8.dp))

            group.members.forEach { item ->
                val isKeeper = item.uri == keeperUri
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp),
                    verticalAlignment = Alignment.Top,
                ) {
                    Checkbox(
                        checked = !isKeeper && item.uri in selectedUris,
                        enabled = enabled && !isKeeper,
                        onCheckedChange = { checked -> onCheckedChange(item.uri, checked) },
                    )
                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .padding(top = 8.dp),
                    ) {
                        Text(item.name, fontWeight = FontWeight.Medium)
                        Text(
                            if (isKeeper) "KEEPER · protected" else "EXACT COPY · SHA-256 matched",
                            style = MaterialTheme.typography.labelSmall,
                            color = if (isKeeper) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Text(item.relativePath, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(item.sizeBytes.toReadableSize(), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        if (!isKeeper) {
                            TextButton(enabled = enabled, onClick = { onKeepThis(item.uri) }) {
                                Text("KEEP THIS COPY")
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ReviewItemCard(
    item: ScanItem,
    checked: Boolean,
    enabled: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Checkbox(
                checked = checked,
                enabled = enabled,
                onCheckedChange = onCheckedChange,
            )
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(top = 8.dp),
            ) {
                Text(item.name, fontWeight = FontWeight.Medium)
                Text(
                    item.kind.reviewLabel(),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(item.relativePath, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (!item.isDirectory) {
                    Text(item.sizeBytes.toReadableSize(), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    if (item.kind == ScanItemKind.OLD_DOWNLOAD || item.kind == ScanItemKind.OLD_SCREENSHOT) {
                        item.lastModifiedMillis.toAgeDays()?.let { ageDays ->
                            Text(
                                "แก้ไขล่าสุดประมาณ $ageDays วันที่แล้ว",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )

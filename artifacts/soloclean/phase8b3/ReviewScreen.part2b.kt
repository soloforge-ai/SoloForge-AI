                            },
                            onKeepThis = { newKeeperUri ->
                                val groupUris = group.members.mapTo(mutableSetOf()) { it.uri }
                                keeperByGroup = keeperByGroup + (group.groupId to newKeeperUri)
                                selectedUris = (selectedUris - groupUris) + (groupUris - newKeeperUri)
                            },
                        )
                    }
                }
            }

            val kinds = listOf(
                ScanItemKind.APP_LEFTOVER,
                ScanItemKind.OLD_DOWNLOAD,
                ScanItemKind.OLD_SCREENSHOT,
                ScanItemKind.APK_OR_ZIP,
                ScanItemKind.LARGE_FILE,
                ScanItemKind.EMPTY_FOLDER,
            )

            kinds.forEach { kind ->
                val kindItems = standardCandidates.filter { it.kind == kind }
                if (kindItems.isNotEmpty()) {
                    item(key = "header-$kind") {
                        val kindUris = kindItems.mapTo(mutableSetOf()) { it.uri }
                        CategoryHeader(
                            title = kind.categoryTitle(),
                            count = kindItems.size,
                            bytes = kindItems.filterNot { it.isDirectory }.sumOf { it.sizeBytes },
                            selectedCount = kindUris.count { it in selectedUris },
                            expanded = kind in expandedKinds,
                            enabled = !isCleaning,
                            onToggle = { toggleKind(kind) },
                            onSelectAll = { selectUris(kindUris) },
                            onClear = { clearUris(kindUris) },
                        )
                    }
                    if (kind in expandedKinds) {
                        items(
                            items = kindItems.filter { !showSelectedOnly || it.uri in selectedUris },
                            key = { "item-${it.uri}" },
                        ) { item ->
                            ReviewItemCard(
                                item = item,
                                checked = item.uri in selectedUris,
                                enabled = !isCleaning,
                                onCheckedChange = { checked ->
                                    selectedUris = if (checked) selectedUris + item.uri else selectedUris - item.uri
                                },
                            )
                        }
                    }
                }
            }

            if (allVisibleItems.isEmpty()) {
                item {
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp)) {
                            Text("ไม่มีรายการเหลือใน Cleanup Session", fontWeight = FontWeight.SemiBold)
                            Text(
                                "กด Full Scan หากต้องการค้นหารายการใหม่ที่เกิดขึ้นหลังการลบ",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }

            item {
                OutlinedButton(
                    enabled = !isCleaning,
                    onClick = onBack,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("BACK TO RESULT")
                }
            }
        }
    }
}

@Composable
private fun CategoryHeader(
    title: String,
    count: Int,
    bytes: Long,
    selectedCount: Int,
    expanded: Boolean,
    enabled: Boolean,
    onToggle: () -> Unit,
    onSelectAll: () -> Unit,
    onClear: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(title, fontWeight = FontWeight.SemiBold)
                    Text(
                        buildString {
                            append("$count items")
                            if (bytes > 0L) append(" · ${bytes.toReadableSize()}")
                            append(" · $selectedCount selected")
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                TextButton(enabled = enabled, onClick = onToggle) {
                    Text(if (expanded) "COLLAPSE" else "EXPAND")
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                OutlinedButton(
                    enabled = enabled && selectedCount < count,
                    onClick = onSelectAll,
                    modifier = Modifier.weight(1f),
                ) {
                    Text("SELECT ALL")
                }
                OutlinedButton(
                    enabled = enabled && selectedCount > 0,

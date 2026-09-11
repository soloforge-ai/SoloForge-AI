                            else -> "CLEAN ${selectedItems.size} ITEMS"
                        }
                        Text(label)
                    }
                }
            }
        },
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
            contentPadding = PaddingValues(horizontal = 20.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            item {
                Text(
                    "Review cleanup",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    "เลือกเป็นหมวด ลบเป็นชุด แล้วเลือกต่อได้ใน Session เดิม",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text(
                            "Selected ${selectedItems.size} / $maxDeletableItems",
                            fontWeight = FontWeight.SemiBold,
                        )
                        Text(
                            "ไฟล์ที่เลือก ${selectedBytes.toReadableSize()}",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        if (sessionReclaimedBytes > 0L) {
                            Text(
                                "Session reclaimed ${sessionReclaimedBytes.toReadableSize()}",
                                color = MaterialTheme.colorScheme.primary,
                            )
                        }
                        Spacer(Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            OutlinedButton(
                                enabled = !isCleaning,
                                onClick = { showSelectedOnly = !showSelectedOnly },
                                modifier = Modifier.weight(1f),
                            ) {
                                Text(if (showSelectedOnly) "SHOW ALL" else "SELECTED ONLY")
                            }
                            OutlinedButton(
                                enabled = !isCleaning,
                                onClick = onFullScan,
                                modifier = Modifier.weight(1f),
                            ) {
                                Text("FULL SCAN")
                            }
                        }
                    }
                }
            }

            if (!canWrite) {
                item {
                    Text(
                        "โฟลเดอร์นี้มีสิทธิ์อ่านอย่างเดียว จึงยังลบไม่ได้ กรุณากลับหน้า Home แล้วเลือกโฟลเดอร์ที่อนุญาต Read + Write",
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            cleanupError?.let { message ->
                item {
                    Text(
                        message,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            lastBatchSummary?.let { batch ->
                item {
                    BatchResultCard(batch)
                }
            }

            if (duplicateGroups.isNotEmpty()) {
                item {
                    val duplicateSelectableUris = duplicateGroups.flatMap { group ->
                        val keeper = keeperByGroup[group.groupId] ?: group.defaultKeeperUri
                        group.members.filter { it.uri != keeper }.map { it.uri }
                    }.toSet()
                    CategoryHeader(
                        title = "Exact duplicates",
                        count = duplicateGroups.sumOf { it.members.size },
                        bytes = duplicateGroups.sumOf { it.reclaimableBytes },
                        selectedCount = duplicateSelectableUris.count { it in selectedUris },
                        expanded = ScanItemKind.DUPLICATE_FILE in expandedKinds,
                        enabled = !isCleaning,
                        onToggle = { toggleKind(ScanItemKind.DUPLICATE_FILE) },
                        onSelectAll = { selectUris(duplicateSelectableUris) },
                        onClear = { clearUris(duplicateSelectableUris) },
                    )
                }
                if (ScanItemKind.DUPLICATE_FILE in expandedKinds) {
                    items(
                        items = duplicateGroups.filter { group ->
                            !showSelectedOnly || group.members.any { it.uri in selectedUris }
                        },
                        key = { "duplicate-${it.groupId}" },
                    ) { group ->
                        val currentKeeper = keeperByGroup[group.groupId] ?: group.defaultKeeperUri
                        DuplicateGroupCard(
                            group = group,
                            keeperUri = currentKeeper,
                            selectedUris = selectedUris,
                            enabled = !isCleaning,
                            onCheckedChange = { uri, checked ->
                                if (uri != currentKeeper) {
                                    selectedUris = if (checked) selectedUris + uri else selectedUris - uri
                                }

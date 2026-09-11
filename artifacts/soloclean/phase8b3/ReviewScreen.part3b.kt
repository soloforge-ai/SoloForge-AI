                        }
                    }
                    if (item.kind == ScanItemKind.APP_LEFTOVER) {
                        val score = item.leftoverConfidenceScore ?: 0
                        Text(
                            "${OrphanRules.confidenceLabel(score)} confidence · $score/100 · ${item.leftoverPackageName ?: "unknown package"}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.tertiary,
                        )
                        item.leftoverReasons.take(3).forEach { reason ->
                            Text("• $reason", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }
    }
}

private data class CleaningProgress(
    val current: Int,
    val total: Int,
    val itemName: String,
)

private data class ReviewData(
    val standardCandidates: List<ScanItem>,
    val duplicateGroups: List<DuplicateReviewGroup>,
)

private data class DuplicateReviewGroup(
    val groupId: String,
    val members: List<ScanItem>,
    val defaultKeeperUri: String,
    val reclaimableBytes: Long,
)

private fun buildReviewData(summary: ScanSummary): ReviewData {
    val allItems = summary.categories.flatMap { it.items }
    val duplicateItems = allItems
        .filter { it.kind == ScanItemKind.DUPLICATE_FILE }
        .filter { !it.duplicateGroupId.isNullOrBlank() }

    val duplicateGroups = duplicateItems
        .groupBy { requireNotNull(it.duplicateGroupId) }
        .mapNotNull { (groupId, members) ->
            val uniqueMembers = members.distinctBy { it.uri }
            if (uniqueMembers.size < 2) return@mapNotNull null
            val keeper = uniqueMembers.firstOrNull { it.uri == it.duplicateKeeperUri } ?: uniqueMembers.first()
            DuplicateReviewGroup(
                groupId = groupId,
                members = uniqueMembers.sortedWith(
                    compareBy<ScanItem> { if (it.uri == keeper.uri) 0 else 1 }
                        .thenBy { it.relativePath.lowercase() },
                ),
                defaultKeeperUri = keeper.uri,
                reclaimableBytes = uniqueMembers.sumOf { it.sizeBytes } - keeper.sizeBytes,
            )
        }
        .sortedByDescending { it.reclaimableBytes }

    val duplicateUris = duplicateGroups
        .flatMap { it.members }
        .mapTo(mutableSetOf()) { it.uri }

    val standardCandidates = allItems
        .filterNot { it.kind == ScanItemKind.DUPLICATE_FILE }
        .filterNot { it.uri in duplicateUris }
        .groupBy { it.uri }
        .values
        .map { sameUriItems ->
            sameUriItems.firstOrNull { it.kind == ScanItemKind.APP_LEFTOVER }
                ?: sameUriItems.firstOrNull { it.kind == ScanItemKind.APK_OR_ZIP }
                ?: sameUriItems.firstOrNull { it.kind == ScanItemKind.OLD_SCREENSHOT }
                ?: sameUriItems.firstOrNull { it.kind == ScanItemKind.OLD_DOWNLOAD }
                ?: sameUriItems.firstOrNull { it.kind == ScanItemKind.LARGE_FILE }
                ?: sameUriItems.first()
        }
        .sortedWith(
            compareBy<ScanItem> { it.kind.reviewOrder() }
                .thenByDescending { it.sizeBytes }
                .thenBy { it.relativePath.lowercase() },
        )

    return ReviewData(
        standardCandidates = standardCandidates,
        duplicateGroups = duplicateGroups,
    )
}

private fun defaultSelectedUris(reviewData: ReviewData): Set<String> = buildSet {
    reviewData.standardCandidates
        .filter(CleanupSafetyPolicy::isDefaultSelected)
        .forEach { add(it.uri) }

    reviewData.duplicateGroups.forEach { group ->
        group.members
            .filter { it.uri != group.defaultKeeperUri }
            .forEach { add(it.uri) }
    }
}

private fun ScanItemKind.categoryTitle(): String = when (this) {
    ScanItemKind.DUPLICATE_FILE -> "Exact duplicates"
    ScanItemKind.APP_LEFTOVER -> "Possible app leftovers"
    ScanItemKind.OLD_DOWNLOAD -> "Old downloads"
    ScanItemKind.OLD_SCREENSHOT -> "Old screenshots"
    ScanItemKind.APK_OR_ZIP -> "APK / ZIP"
    ScanItemKind.LARGE_FILE -> "Large files"
    ScanItemKind.EMPTY_FOLDER -> "Empty folders"
}

private fun ScanItemKind.reviewOrder(): Int = when (this) {
    ScanItemKind.APP_LEFTOVER -> 0
    ScanItemKind.OLD_DOWNLOAD -> 1
    ScanItemKind.OLD_SCREENSHOT -> 2
    ScanItemKind.APK_OR_ZIP -> 3
    ScanItemKind.LARGE_FILE -> 4
    ScanItemKind.EMPTY_FOLDER -> 5
    ScanItemKind.DUPLICATE_FILE -> 6
}

private fun ScanItemKind.reviewLabel(): String = when (this) {
    ScanItemKind.EMPTY_FOLDER -> "EMPTY FOLDER · manual selection"
    ScanItemKind.APP_LEFTOVER -> "POSSIBLE APP LEFTOVER · manual selection"
    ScanItemKind.OLD_DOWNLOAD -> "OLD DOWNLOAD · manual selection"
    ScanItemKind.OLD_SCREENSHOT -> "OLD SCREENSHOT · manual selection"
    ScanItemKind.APK_OR_ZIP -> "APK / ZIP · review first"
    ScanItemKind.LARGE_FILE -> "LARGE FILE · manual selection"
    ScanItemKind.DUPLICATE_FILE -> "EXACT DUPLICATE · grouped above"
}

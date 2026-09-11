package com.soloforge.soloclean.cleanup

import com.soloforge.soloclean.data.model.CleanupItemResult
import com.soloforge.soloclean.data.model.CleanupStatus
import com.soloforge.soloclean.data.model.CleanupSummary
import com.soloforge.soloclean.data.model.ScanItem
import com.soloforge.soloclean.data.model.ScanItemKind
import org.junit.Assert.assertEquals
import org.junit.Test

class CleanupSessionRulesTest {
    @Test
    fun successfulUris_onlyReturnsSuccessfulItems() {
        val success = item("content://success")
        val skipped = item("content://skipped")
        val failed = item("content://failed")

        val uris = CleanupSessionRules.successfulUris(
            listOf(
                CleanupItemResult(success, CleanupStatus.SUCCESS),
                CleanupItemResult(skipped, CleanupStatus.SKIPPED),
                CleanupItemResult(failed, CleanupStatus.FAILED),
            ),
        )

        assertEquals(setOf(success.uri), uris)
    }

    @Test
    fun mergeSummaries_keepsQueueResultOrder() {
        val first = CleanupSummary(
            results = listOf(CleanupItemResult(item("content://1"), CleanupStatus.SUCCESS)),
            startedAtMillis = 10L,
            finishedAtMillis = 20L,
        )
        val second = CleanupSummary(
            results = listOf(CleanupItemResult(item("content://2"), CleanupStatus.SKIPPED)),
            startedAtMillis = 21L,
            finishedAtMillis = 30L,
        )

        val merged = CleanupSessionRules.mergeSummaries(
            summaries = listOf(first, second),
            startedAtMillis = 10L,
            finishedAtMillis = 30L,
        )

        assertEquals(listOf("content://1", "content://2"), merged.results.map { it.item.uri })
        assertEquals(1, merged.successCount)
        assertEquals(1, merged.skippedCount)
    }

    private fun item(uri: String) = ScanItem(
        uri = uri,
        name = uri.substringAfterLast('/'),
        relativePath = uri,
        sizeBytes = 100L,
        lastModifiedMillis = 1L,
        kind = ScanItemKind.APK_OR_ZIP,
    )
}

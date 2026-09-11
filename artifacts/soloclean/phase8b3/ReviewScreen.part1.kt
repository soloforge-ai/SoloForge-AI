package com.soloforge.soloclean.ui.review

import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.soloforge.soloclean.cleanup.CleanupEngine
import com.soloforge.soloclean.cleanup.CleanupSafetyPolicy
import com.soloforge.soloclean.cleanup.CleanupSessionRules
import com.soloforge.soloclean.data.model.CleanupSummary
import com.soloforge.soloclean.data.model.ScanItem
import com.soloforge.soloclean.data.model.ScanItemKind
import com.soloforge.soloclean.data.model.ScanSummary
import com.soloforge.soloclean.scanner.OrphanRules
import com.soloforge.soloclean.util.toAgeDays
import com.soloforge.soloclean.util.toReadableSize
import kotlinx.coroutines.launch

@Composable
fun ReviewScreen(
    summary: ScanSummary,
    treeUri: Uri?,
    canWrite: Boolean,
    cleanupEngine: CleanupEngine,
    onBack: () -> Unit,
    onFullScan: () -> Unit,
    onSessionStorageChanged: () -> Unit,
) {
    val initialReviewData = remember(summary.finishedAtMillis) { buildReviewData(summary) }
    var standardCandidates by remember(summary.finishedAtMillis) {
        mutableStateOf(initialReviewData.standardCandidates)
    }
    var duplicateGroups by remember(summary.finishedAtMillis) {
        mutableStateOf(initialReviewData.duplicateGroups)
    }
    var keeperByGroup by remember(summary.finishedAtMillis) {
        mutableStateOf(
            initialReviewData.duplicateGroups.associate { group -> group.groupId to group.defaultKeeperUri },
        )
    }
    var selectedUris by remember(summary.finishedAtMillis) {
        mutableStateOf(defaultSelectedUris(initialReviewData))
    }
    var expandedKinds by remember(summary.finishedAtMillis) {
        mutableStateOf(setOf(ScanItemKind.DUPLICATE_FILE))
    }
    var showSelectedOnly by remember(summary.finishedAtMillis) { mutableStateOf(false) }
    var showConfirmation by remember { mutableStateOf(false) }
    var isCleaning by remember { mutableStateOf(false) }
    var cleaningProgress by remember { mutableStateOf<CleaningProgress?>(null) }
    var cleanupError by remember { mutableStateOf<String?>(null) }
    var lastBatchSummary by remember { mutableStateOf<CleanupSummary?>(null) }
    var sessionReclaimedBytes by remember { mutableStateOf(0L) }
    val scope = rememberCoroutineScope()

    val allVisibleItems = standardCandidates + duplicateGroups.flatMap { it.members }
    val selectedItems = allVisibleItems
        .filter { it.uri in selectedUris }
        .map { item ->
            if (item.kind == ScanItemKind.DUPLICATE_FILE) {
                val groupId = item.duplicateGroupId
                item.copy(duplicateKeeperUri = groupId?.let(keeperByGroup::get))
            } else {
                item
            }
        }
        .distinctBy { it.uri }

    val selectedBytes = selectedItems
        .filterNot { it.isDirectory }
        .sumOf { it.sizeBytes }
    val maxDeletableItems = standardCandidates.size +
        duplicateGroups.sumOf { (it.members.size - 1).coerceAtLeast(0) }

    fun toggleKind(kind: ScanItemKind) {
        expandedKinds = if (kind in expandedKinds) expandedKinds - kind else expandedKinds + kind
    }

    fun selectUris(uris: Set<String>) {
        selectedUris = selectedUris + uris
    }

    fun clearUris(uris: Set<String>) {
        selectedUris = selectedUris - uris
    }

    if (showConfirmation) {
        AlertDialog(
            onDismissRequest = {
                if (!isCleaning) showConfirmation = false
            },
            title = { Text("ยืนยันการลบ") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("กำลังจะลบ ${selectedItems.size} รายการ")
                    Text("พื้นที่ไฟล์ที่เลือก ${selectedBytes.toReadableSize()}")
                    Text(
                        "ระบบจะลบทีละรายการและตรวจ Safety Policy ซ้ำก่อนลบทุกไฟล์ รายการที่ลบสำเร็จจะหายจาก Session ทันที",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    if (selectedItems.any { it.kind == ScanItemKind.DUPLICATE_FILE }) {
                        Text(
                            "Exact duplicates จะตรวจ SHA-256 ซ้ำทั้งไฟล์ที่จะลบและ Keeper ก่อนลบจริง",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    Text(
                        "หลังจบชุดนี้คุณเลือกไฟล์อื่นลบต่อได้โดยไม่ต้อง Full Scan ใหม่",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            },
            confirmButton = {
                TextButton(
                    enabled = !isCleaning,
                    onClick = {
                        val targetTree = treeUri
                        if (targetTree == null || !canWrite) {
                            cleanupError = "ไม่มีสิทธิ์เขียนในโฟลเดอร์นี้ กรุณากลับไปเลือกโฟลเดอร์ใหม่"
                            showConfirmation = false
                            return@TextButton
                        }
                        if (selectedItems.isEmpty()) {
                            showConfirmation = false
                            return@TextButton
                        }

                        isCleaning = true
                        cleanupError = null
                        lastBatchSummary = null
                        val queue = selectedItems.toList()
                        scope.launch {
                            val startedAt = System.currentTimeMillis()
                            val summaries = mutableListOf<CleanupSummary>()

                            queue.forEachIndexed { index, item ->
                                cleaningProgress = CleaningProgress(
                                    current = index + 1,
                                    total = queue.size,
                                    itemName = item.name,
                                )
                                val one = runCatching {
                                    cleanupEngine.cleanup(targetTree, listOf(item))
                                }.getOrElse { error ->
                                    cleanupError = error.message ?: "Cleanup บางรายการล้มเหลว"
                                    CleanupSummary.Empty
                                }
                                summaries += one
                            }

                            val batchSummary = CleanupSessionRules.mergeSummaries(
                                summaries = summaries,
                                startedAtMillis = startedAt,
                                finishedAtMillis = System.currentTimeMillis(),
                            )
                            val successfulUris = CleanupSessionRules.successfulUris(batchSummary.results)
                            val attemptedUris = queue.mapTo(mutableSetOf()) { it.uri }

                            standardCandidates = standardCandidates.filterNot { it.uri in successfulUris }
                            duplicateGroups = duplicateGroups.mapNotNull { group ->
                                val remainingMembers = group.members.filterNot { it.uri in successfulUris }
                                if (remainingMembers.size < 2) {
                                    null
                                } else {
                                    val currentKeeper = keeperByGroup[group.groupId]
                                    val nextKeeper = remainingMembers.firstOrNull { it.uri == currentKeeper }
                                        ?: remainingMembers.first()
                                    group.copy(
                                        members = remainingMembers,
                                        defaultKeeperUri = nextKeeper.uri,
                                        reclaimableBytes = remainingMembers.sumOf { it.sizeBytes } - nextKeeper.sizeBytes,
                                    )
                                }
                            }
                            val activeGroupIds = duplicateGroups.mapTo(mutableSetOf()) { it.groupId }
                            keeperByGroup = keeperByGroup.filterKeys { it in activeGroupIds }

                            selectedUris = selectedUris - attemptedUris - successfulUris
                            showSelectedOnly = false
                            sessionReclaimedBytes += batchSummary.reclaimedBytes
                            lastBatchSummary = batchSummary
                            if (batchSummary.successCount > 0) onSessionStorageChanged()
                            cleaningProgress = null
                            isCleaning = false
                            showConfirmation = false
                        }
                    },
                ) {
                    Text("DELETE QUEUE")
                }
            },
            dismissButton = {
                TextButton(
                    enabled = !isCleaning,
                    onClick = { showConfirmation = false },
                ) {
                    Text("CANCEL")
                }
            },
        )
    }

    Scaffold(
        bottomBar = {
            Surface(shadowElevation = 8.dp) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 10.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    cleaningProgress?.let { progress ->
                        Text(
                            "Deleting ${progress.current} / ${progress.total} · ${progress.itemName}",
                            style = MaterialTheme.typography.bodySmall,
                            maxLines = 1,
                        )
                        LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                    }
                    Button(
                        enabled = selectedItems.isNotEmpty() && canWrite && treeUri != null && !isCleaning,
                        onClick = { showConfirmation = true },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        val label = when {
                            isCleaning -> "CLEANING..."
                            selectedItems.isEmpty() -> "SELECT FILES TO CLEAN"
                            selectedBytes > 0L -> "CLEAN ${selectedBytes.toReadableSize()} · ${selectedItems.size} ITEMS"

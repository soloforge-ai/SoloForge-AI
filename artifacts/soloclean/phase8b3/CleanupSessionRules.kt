package com.soloforge.soloclean.cleanup

import com.soloforge.soloclean.data.model.CleanupItemResult
import com.soloforge.soloclean.data.model.CleanupStatus
import com.soloforge.soloclean.data.model.CleanupSummary

object CleanupSessionRules {
    fun successfulUris(results: List<CleanupItemResult>): Set<String> =
        results.asSequence()
            .filter { it.status == CleanupStatus.SUCCESS }
            .map { it.item.uri }
            .toSet()

    fun mergeSummaries(
        summaries: List<CleanupSummary>,
        startedAtMillis: Long,
        finishedAtMillis: Long,
    ): CleanupSummary = CleanupSummary(
        results = summaries.flatMap { it.results },
        startedAtMillis = startedAtMillis,
        finishedAtMillis = finishedAtMillis,
    )
}

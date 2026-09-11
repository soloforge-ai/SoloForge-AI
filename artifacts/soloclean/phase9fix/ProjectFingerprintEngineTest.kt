package com.soloforge.soloclean.project

import com.soloforge.soloclean.data.model.FileRecord
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProjectFingerprintEngineTest {
    private val engine = ProjectFingerprintEngine()
    private val tia = ProjectDefinition("tia", "Try It Again", listOf("TIA", "try_it_again"), 1L)

    @Test
    fun explicitAliasCreatesCandidateWithEvidence() {
        val file = file("TIA_teaser_final.mp4", "Download/TIA_teaser_final.mp4")
        val result = engine.analyze(listOf(file), listOf(tia)).single()
        assertEquals(1, result.suggestedFiles.size)
        assertTrue(result.suggestedFiles.single().evidence.any { it.signalType == "project-keyword" })
    }

    @Test
    fun nearbySiblingCanJoinThroughDirectoryAndTimeSignals() {
        val anchor = file("TIA_scene01.png", "Download/teaser/TIA_scene01.png", 1_000_000L)
        val sibling = file("export_0911.mp4", "Download/teaser/export_0911.mp4", 1_030_000L)
        val result = engine.analyze(listOf(anchor, sibling), listOf(tia)).single()
        val candidate = result.candidates.first { it.file.uri == sibling.uri }
        assertTrue(candidate.confidence >= 35)
        assertTrue(candidate.evidence.any { it.signalType == "directory-family" })
        assertTrue(candidate.evidence.any { it.signalType == "time-proximity" })
    }

    @Test
    fun shortAliasDoesNotMatchInsideUnrelatedWord() {
        val unrelated = file("essential_notes.txt", "Download/docs/essential_notes.txt", 4_000_000L)
        val result = engine.analyze(listOf(unrelated), listOf(tia)).single()
        assertTrue(result.candidates.isEmpty())
    }

    @Test
    fun unrelatedFileIsNotSuggested() {
        val unrelated = file("tax_2024.pdf", "Download/docs/tax_2024.pdf", 4_000_000L)
        val result = engine.analyze(listOf(unrelated), listOf(tia)).single()
        assertTrue(result.candidates.isEmpty())
    }

    @Test
    fun userConfirmationOverridesScoreAndOtherProjects() {
        val file = file("export.mp4", "Download/export.mp4")
        val other = ProjectDefinition("other", "SoloForge", listOf("SF"), 2L)
        val decision = ProjectFileDecision(file.uri, tia.id, ProjectCandidateStatus.CONFIRMED)
        val analyses = engine.analyze(listOf(file), listOf(tia, other), listOf(decision))
        assertEquals(ProjectCandidateStatus.CONFIRMED, analyses.first { it.project.id == tia.id }.candidates.single().status)
        assertTrue(analyses.first { it.project.id == other.id }.candidates.isEmpty())
    }

    @Test
    fun rejectIsScopedToOneProject() {
        val file = file("shared_TIA_SF.png", "Download/shared_TIA_SF.png")
        val other = ProjectDefinition("other", "SoloForge", listOf("SF"), 2L)
        val reject = ProjectFileDecision(file.uri, tia.id, ProjectCandidateStatus.REJECTED)
        val analyses = engine.analyze(listOf(file), listOf(tia, other), listOf(reject))
        assertEquals(ProjectCandidateStatus.REJECTED, analyses.first { it.project.id == tia.id }.candidates.single().status)
        assertFalse(analyses.first { it.project.id == other.id }.candidates.isEmpty())
    }

    private fun file(name: String, path: String, modified: Long = 1_000_000L) = FileRecord(
        uri = "content://$path",
        name = name,
        relativePath = path,
        sizeBytes = 1024L,
        lastModifiedMillis = modified,
        mimeType = null,
    )
}

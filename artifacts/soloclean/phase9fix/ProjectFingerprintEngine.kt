package com.soloforge.soloclean.project

import com.soloforge.soloclean.data.model.FileRecord
import kotlin.math.abs

class ProjectFingerprintEngine(
    private val candidateThreshold: Int = 35,
) {
    fun analyze(
        files: List<FileRecord>,
        projects: List<ProjectDefinition>,
        decisions: List<ProjectFileDecision> = emptyList(),
    ): List<ProjectAnalysis> {
        val confirmedAssignmentByUri = decisions
            .filter { it.status == ProjectCandidateStatus.CONFIRMED }
            .associateBy { it.fileUri }
        return projects.map { project ->
            val projectDecisions = decisions.filter { it.projectId == project.id }
            val confirmedUris = projectDecisions
                .filter { it.status == ProjectCandidateStatus.CONFIRMED }
                .mapTo(mutableSetOf()) { it.fileUri }

            val keywordAnchors = files.filter { file ->
                keywordEvidence(file, project).isNotEmpty() || file.uri in confirmedUris
            }

            val candidates = files.mapNotNull { file ->
                val confirmedAssignment = confirmedAssignmentByUri[file.uri]
                if (confirmedAssignment != null && confirmedAssignment.projectId != project.id) return@mapNotNull null
                val forced = decisions.lastOrNull { it.fileUri == file.uri && it.projectId == project.id }
                if (forced?.status == ProjectCandidateStatus.REJECTED) return@mapNotNull ProjectCandidate(
                    file = file,
                    projectId = project.id,
                    confidence = 0,
                    status = ProjectCandidateStatus.REJECTED,
                    evidence = emptyList(),
                )

                val evidence = scoreEvidence(file, project, keywordAnchors, confirmedUris)
                val score = evidence.sumOf { it.scoreContribution }.coerceIn(0, 100)
                val status = when {
                    forced?.status == ProjectCandidateStatus.CONFIRMED -> ProjectCandidateStatus.CONFIRMED
                    forced?.status == ProjectCandidateStatus.REJECTED -> ProjectCandidateStatus.REJECTED
                    score >= candidateThreshold -> ProjectCandidateStatus.SUGGESTED
                    else -> return@mapNotNull null
                }
                ProjectCandidate(file, project.id, score, status, evidence)
            }.sortedWith(
                compareBy<ProjectCandidate> { it.status != ProjectCandidateStatus.CONFIRMED }
                    .thenByDescending { it.confidence }
                    .thenByDescending { it.file.lastModifiedMillis }
                    .thenBy { it.file.relativePath.lowercase() },
            )

            ProjectAnalysis(project, candidates)
        }
    }

    private fun scoreEvidence(
        file: FileRecord,
        project: ProjectDefinition,
        anchors: List<FileRecord>,
        confirmedUris: Set<String>,
    ): List<ProjectMatchEvidence> = buildList {
        addAll(keywordEvidence(file, project))

        if (file.uri in confirmedUris) {
            add(ProjectMatchEvidence("user-confirmed", "ผู้ใช้ยืนยันไฟล์นี้แล้ว", 100))
            return@buildList
        }

        val relatedAnchors = anchors.asSequence().filter { it.uri != file.uri }.toList()
        if (relatedAnchors.any { it.parentPath.isNotBlank() && it.parentPath == file.parentPath }) {
            add(ProjectMatchEvidence("directory-family", "อยู่ในโฟลเดอร์เดียวกับไฟล์ anchor", 25))
        }
        if (relatedAnchors.any { closeInTime(it, file) }) {
            add(ProjectMatchEvidence("time-proximity", "แก้ไขใกล้กับไฟล์ของโปรเจกต์ภายใน 2 ชั่วโมง", 15))
        }
        if (relatedAnchors.any { relatedMediaType(it, file) }) {
            add(ProjectMatchEvidence("media-relationship", "ชนิดไฟล์สัมพันธ์กับ asset ในโปรเจกต์", 10))
        }
        val similarity = relatedAnchors.maxOfOrNull { filenameSimilarity(it.name, file.name) } ?: 0
        if (similarity >= 60) {
            add(ProjectMatchEvidence("filename-similarity", "ชื่อไฟล์อยู่ใน filename family เดียวกัน", 10))
        }
        if (VERSION_PATTERN.containsMatchIn(file.name)) {
            add(ProjectMatchEvidence("version-pattern", "ชื่อไฟล์มีรูปแบบ version/final/copy", 5))
        }
    }

    private fun keywordEvidence(file: FileRecord, project: ProjectDefinition): List<ProjectMatchEvidence> {
        val rawHaystack = "${file.name} ${file.relativePath}"
        val phrases = buildList {
            add(project.name)
            addAll(project.aliases)
        }.filter { normalize(it).length >= 2 }.distinct()

        return if (phrases.any { phraseMatches(rawHaystack, it) }) {
            listOf(ProjectMatchEvidence("project-keyword", "ชื่อ/เส้นทางตรงกับชื่อหรือ alias ของโปรเจกต์", 35))
        } else {
            emptyList()
        }
    }

    /**
     * Short aliases such as TIA/SF are matched as filename/path tokens, not arbitrary
     * substrings. This avoids false positives such as alias `TIA` matching
     * `essential_notes.txt`. Longer project phrases still use normalized matching so
     * `Try It Again`, `try_it_again`, and `try-it-again` remain equivalent.
     */
    private fun phraseMatches(rawHaystack: String, phrase: String): Boolean {
        val normalizedPhrase = normalize(phrase)
        if (normalizedPhrase.isBlank()) return false
        if (normalizedPhrase.length <= SHORT_ALIAS_MAX_LENGTH) {
            val tokens = rawHaystack
                .lowercase()
                .split(Regex("[^a-z0-9ก-๙]+"))
                .map(::normalize)
                .filter { it.isNotBlank() }
            return normalizedPhrase in tokens
        }
        return normalize(rawHaystack).contains(normalizedPhrase)
    }

    private fun normalize(value: String): String = value
        .lowercase()
        .replace(Regex("[^a-z0-9ก-๙]+"), "")

    private fun closeInTime(a: FileRecord, b: FileRecord): Boolean {
        if (a.lastModifiedMillis <= 0L || b.lastModifiedMillis <= 0L) return false
        return abs(a.lastModifiedMillis - b.lastModifiedMillis) <= TWO_HOURS_MS
    }

    private fun relatedMediaType(a: FileRecord, b: FileRecord): Boolean {
        val familyA = mediaFamily(a.extension)
        val familyB = mediaFamily(b.extension)
        if (familyA == "other" || familyB == "other") return false
        return familyA == familyB || setOf(familyA, familyB) == setOf("image", "video")
    }

    private fun mediaFamily(extension: String): String = when (extension) {
        "png", "jpg", "jpeg", "webp", "gif", "heic" -> "image"
        "mp4", "mov", "mkv", "webm", "avi" -> "video"
        "wav", "mp3", "m4a", "aac", "flac" -> "audio"
        "md", "txt", "doc", "docx", "pdf" -> "document"
        "zip", "7z", "rar", "tar", "gz" -> "archive"
        else -> "other"
    }

    private fun filenameSimilarity(a: String, b: String): Int {
        val tokensA = tokenizeFilename(a)
        val tokensB = tokenizeFilename(b)
        if (tokensA.isEmpty() || tokensB.isEmpty()) return 0
        val intersection = tokensA.intersect(tokensB).size.toDouble()
        val union = tokensA.union(tokensB).size.toDouble()
        return ((intersection / union) * 100.0).toInt()
    }

    private fun tokenizeFilename(value: String): Set<String> = value
        .substringBeforeLast('.')
        .lowercase()
        .replace(VERSION_PATTERN, " ")
        .split(Regex("[^a-z0-9ก-๙]+"))
        .filter { it.length >= 2 }
        .toSet()

    companion object {
        private const val TWO_HOURS_MS = 2L * 60L * 60L * 1000L
        private const val SHORT_ALIAS_MAX_LENGTH = 4
        private val VERSION_PATTERN = Regex("(?i)(?:^|[_ .-])(v\\d+|final\\d*|copy|draft|upscale|export|render|\\(\\d+\\))(?:$|[_ .-])")
    }
}

from pathlib import Path
import re

root = Path("soloclean/app/src/main/java/com/soloforge/soloclean")
test_root = Path("soloclean/app/src/test/java/com/soloforge/soloclean")
model = root / "data/model/ScanItem.kt"
scanner = root / "scanner/AndroidReadOnlyScanEngine.kt"
policy = root / "cleanup/CleanupSafetyPolicy.kt"
engine = root / "cleanup/AndroidSafCleanupEngine.kt"
review = root / "ui/review/ReviewScreen.kt"
result_screen = root / "ui/result/ResultScreen.kt"
cache_rules = root / "scanner/CacheRules.kt"
cache_test = test_root / "scanner/CacheRulesTest.kt"
gradle = Path("soloclean/app/build.gradle.kts")

cache_rules.write_text(r'''package com.soloforge.soloclean.scanner

data class CacheMatch(
    val confidenceScore: Int,
    val reason: String,
)

object CacheRules {
    const val DEFAULT_MIN_AGE_DAYS = 7
    const val MIN_CANDIDATE_SCORE = 70

    private val cacheDirectoryMarkers = setOf(
        "cache", ".cache", "caches", "code_cache", "tmp", "temp", ".temp", "thumbnails", ".thumbnails",
    )
    private val cacheExtensions = setOf("tmp", "temp", "cache")

    fun classify(
        relativePath: String,
        fileName: String,
        lastModifiedMillis: Long,
        nowMillis: Long,
        minimumAgeDays: Int = DEFAULT_MIN_AGE_DAYS,
    ): CacheMatch? {
        if (lastModifiedMillis <= 0L || nowMillis <= lastModifiedMillis) return null
        if (!AgeRules.isOlderThan(lastModifiedMillis, nowMillis, minimumAgeDays)) return null

        val normalizedPath = relativePath.replace('\\', '/')
        val segments = normalizedPath.split('/').filter { it.isNotBlank() }
        val parentSegments = if (segments.size > 1) segments.dropLast(1) else emptyList()
        val matchedDirectory = parentSegments.map { it.lowercase() }.firstOrNull { it in cacheDirectoryMarkers }

        val normalizedName = fileName.lowercase()
        val extension = normalizedName.substringAfterLast('.', missingDelimiterValue = "")
        val tempExtension = extension in cacheExtensions
        val thumbData = normalizedName.startsWith(".thumbdata")

        return when {
            matchedDirectory != null -> CacheMatch(
                confidenceScore = 85,
                reason = "อยู่ในโฟลเดอร์ cache/temp ที่ผู้ใช้อนุญาตผ่าน SAF: $matchedDirectory",
            )
            thumbData -> CacheMatch(
                confidenceScore = 80,
                reason = "ชื่อไฟล์ตรงรูปแบบ Android thumbnail cache (.thumbdata)",
            )
            tempExtension -> CacheMatch(
                confidenceScore = 70,
                reason = "นามสกุลไฟล์ .$extension มีลักษณะเป็นไฟล์ชั่วคราว",
            )
            else -> null
        }
    }

    fun isSupportedCandidateMetadata(
        minimumAgeDays: Int?,
        confidenceScore: Int?,
        reason: String?,
    ): Boolean =
        (minimumAgeDays ?: 0) >= DEFAULT_MIN_AGE_DAYS &&
            (confidenceScore ?: 0) >= MIN_CANDIDATE_SCORE &&
            !reason.isNullOrBlank()
}
''')

m = model.read_text()
if "CACHE_OR_TEMP" not in m:
    m = m.replace("    APP_LEFTOVER,\n", "    APP_LEFTOVER,\n    CACHE_OR_TEMP,\n", 1)
field_marker = "    val leftoverReasons: List<String> = emptyList(),\n"
fields = """    /** Conservative 0..100 confidence that this accessible file is disposable cache/temp data. */
    val cacheConfidenceScore: Int? = null,
    /** Human-readable cache/temp signal shown before deletion. */
    val cacheReason: String? = null,
"""
if "val cacheConfidenceScore" not in m:
    if field_marker not in m:
        raise SystemExit("ScanItem leftoverReasons marker missing")
    m = m.replace(field_marker, field_marker + fields, 1)
model.write_text(m)

s = scanner.read_text()
if "private val cacheMinAgeDays" not in s:
    s = s.replace(
        "    private val oldScreenshotDays: Int = AgeRules.DEFAULT_OLD_SCREENSHOT_DAYS,\n",
        "    private val oldScreenshotDays: Int = AgeRules.DEFAULT_OLD_SCREENSHOT_DAYS,\n    private val cacheMinAgeDays: Int = CacheRules.DEFAULT_MIN_AGE_DAYS,\n",
        1,
    )
insert_after = """        if (
            size > 0L &&
            AgeRules.isScreenshotCandidate(fileName, relativePath, file.type) &&
            AgeRules.isOlderThan(lastModified, scanNowMillis, oldScreenshotDays)
        ) {
            accumulator.oldScreenshots += file.toScanItem(
                fileName = fileName,
                relativePath = relativePath,
                size = size,
                lastModified = lastModified,
                kind = ScanItemKind.OLD_SCREENSHOT,
                minimumAgeDays = oldScreenshotDays,
            )
        }

"""
cache_block = """        if (size > 0L) {
            CacheRules.classify(
                relativePath = relativePath,
                fileName = fileName,
                lastModifiedMillis = lastModified,
                nowMillis = scanNowMillis,
                minimumAgeDays = cacheMinAgeDays,
            )?.let { match ->
                accumulator.cacheOrTempFiles += file.toScanItem(
                    fileName = fileName,
                    relativePath = relativePath,
                    size = size,
                    lastModified = lastModified,
                    kind = ScanItemKind.CACHE_OR_TEMP,
                    minimumAgeDays = cacheMinAgeDays,
                    cacheConfidenceScore = match.confidenceScore,
                    cacheReason = match.reason,
                )
            }
        }

"""
if "CacheRules.classify(" not in s:
    if insert_after not in s:
        raise SystemExit("old screenshot block marker missing")
    s = s.replace(insert_after, insert_after + cache_block, 1)
sig_marker = "        leftoverReasons: List<String> = emptyList(),\n"
sig_fields = "        cacheConfidenceScore: Int? = null,\n        cacheReason: String? = null,\n"
if "cacheConfidenceScore: Int? = null" not in s:
    if sig_marker not in s:
        raise SystemExit("toScanItem signature marker missing")
    s = s.replace(sig_marker, sig_marker + sig_fields, 1)
ctor_marker = "        leftoverReasons = leftoverReasons,\n"
ctor_fields = "        cacheConfidenceScore = cacheConfidenceScore,\n        cacheReason = cacheReason,\n"
if "cacheConfidenceScore = cacheConfidenceScore" not in s:
    if ctor_marker not in s:
        raise SystemExit("toScanItem constructor marker missing")
    s = s.replace(ctor_marker, ctor_marker + ctor_fields, 1)
if "val cacheOrTempFiles =" not in s:
    s = s.replace(
        "        val appLeftovers = accumulator.appLeftovers.sortedWith(\n",
        "        val cacheOrTempFiles = accumulator.cacheOrTempFiles.sortedByDescending { it.sizeBytes }\n        val appLeftovers = accumulator.appLeftovers.sortedWith(\n",
        1,
    )
app_category_marker = """            ScanCategoryResult(
                type = ScanItemKind.APP_LEFTOVER,
                title = "Possible app leftovers",
                subtitle = appLeftoverSubtitle,
                totalBytes = appLeftovers.sumOf { it.sizeBytes },
                itemCount = appLeftovers.size,
                items = appLeftovers,
            ),
"""
cache_category = """            ScanCategoryResult(
                type = ScanItemKind.CACHE_OR_TEMP,
                title = "Cache & temporary files",
                subtitle = "ไฟล์ cache/temp ที่เข้าถึงได้ในพื้นที่ SAF และเก่าตั้งแต่ $cacheMinAgeDays วัน — ไม่รวม private cache ของแอปอื่น",
                totalBytes = cacheOrTempFiles.sumOf { it.sizeBytes },
                itemCount = cacheOrTempFiles.size,
                items = cacheOrTempFiles,
            ),
"""
if 'title = "Cache & temporary files"' not in s:
    if app_category_marker not in s:
        raise SystemExit("app leftover category marker missing")
    s = s.replace(app_category_marker, app_category_marker + cache_category, 1)
acc_marker = "        val appLeftovers: MutableList<ScanItem> = mutableListOf(),\n"
if "val cacheOrTempFiles: MutableList<ScanItem>" not in s:
    if acc_marker not in s:
        raise SystemExit("ScanAccumulator appLeftovers marker missing")
    s = s.replace(acc_marker, acc_marker + "        val cacheOrTempFiles: MutableList<ScanItem> = mutableListOf(),\n", 1)
scanner.write_text(s)

p = policy.read_text()
if "import com.soloforge.soloclean.scanner.CacheRules" not in p:
    p = p.replace("import com.soloforge.soloclean.scanner.AgeRules\n", "import com.soloforge.soloclean.scanner.AgeRules\nimport com.soloforge.soloclean.scanner.CacheRules\n", 1)
default_block = p.split("fun isDefaultSelected",1)[1].split("fun isSupportedCandidate",1)[0]
if "ScanItemKind.CACHE_OR_TEMP," not in default_block:
    p = p.replace("        ScanItemKind.APP_LEFTOVER,\n", "        ScanItemKind.APP_LEFTOVER,\n        ScanItemKind.CACHE_OR_TEMP,\n", 1)
supported_marker = """        ScanItemKind.APP_LEFTOVER ->
            !item.isDirectory &&
                item.sizeBytes > 0L &&
                OrphanRules.isSupportedCandidateMetadata(
                    packageName = item.leftoverPackageName,
                    leftoverRootUri = item.leftoverRootUri,
                    leftoverRootPath = item.leftoverRootPath,
                    confidenceScore = item.leftoverConfidenceScore,
                )
"""
cache_supported = """        ScanItemKind.CACHE_OR_TEMP ->
            !item.isDirectory &&
                item.sizeBytes > 0L &&
                item.lastModifiedMillis > 0L &&
                CacheRules.isSupportedCandidateMetadata(
                    minimumAgeDays = item.minimumAgeDays,
                    confidenceScore = item.cacheConfidenceScore,
                    reason = item.cacheReason,
                )
"""
supported_block = p.split("fun isSupportedCandidate",1)[1].split("fun deduplicateForCleanup",1)[0]
if "ScanItemKind.CACHE_OR_TEMP ->" not in supported_block:
    if supported_marker not in p:
        raise SystemExit("APP_LEFTOVER supported marker missing")
    p = p.replace(supported_marker, supported_marker + cache_supported, 1)
policy.write_text(p)

r = review.read_text()
r = r.replace(
    "                    if (item.kind == ScanItemKind.OLD_DOWNLOAD || item.kind == ScanItemKind.OLD_SCREENSHOT) {",
    "                    if (item.kind == ScanItemKind.OLD_DOWNLOAD || item.kind == ScanItemKind.OLD_SCREENSHOT || item.kind == ScanItemKind.CACHE_OR_TEMP) {",
    1,
)
cache_ui_marker = """                    if (item.kind == ScanItemKind.APP_LEFTOVER) {
                        val score = item.leftoverConfidenceScore ?: 0
                        Text(
                            "\${OrphanRules.confidenceLabel(score)} confidence · $score/100 · \${item.leftoverPackageName ?: "unknown package"}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.tertiary,
                        )
                        item.leftoverReasons.take(3).forEach { reason ->
                            Text("• $reason", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
"""
cache_ui = """                    if (item.kind == ScanItemKind.CACHE_OR_TEMP) {
                        val score = item.cacheConfidenceScore ?: 0
                        Text(
                            "CACHE/TEMP confidence · $score/100",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.tertiary,
                        )
                        item.cacheReason?.let { reason ->
                            Text("• $reason", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Text(
                            "เข้าถึงได้เฉพาะพื้นที่ที่คุณอนุญาตผ่าน SAF · ไม่ใช่ private app cache",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
"""
if "CACHE/TEMP confidence" not in r:
    if cache_ui_marker not in r:
        raise SystemExit("Review APP_LEFTOVER UI marker missing")
    r = r.replace(cache_ui_marker, cache_ui_marker + cache_ui, 1)
if 'ScanItemKind.CACHE_OR_TEMP -> "Cache & temporary files"' not in r:
    r = r.replace('    ScanItemKind.APP_LEFTOVER -> "Possible app leftovers"\n', '    ScanItemKind.APP_LEFTOVER -> "Possible app leftovers"\n    ScanItemKind.CACHE_OR_TEMP -> "Cache & temporary files"\n', 1)
if "ScanItemKind.CACHE_OR_TEMP -> 1" not in r:
    r = r.replace(
        "    ScanItemKind.APP_LEFTOVER -> 0\n    ScanItemKind.OLD_DOWNLOAD -> 1\n    ScanItemKind.OLD_SCREENSHOT -> 2\n    ScanItemKind.APK_OR_ZIP -> 3\n    ScanItemKind.LARGE_FILE -> 4\n    ScanItemKind.EMPTY_FOLDER -> 5\n    ScanItemKind.DUPLICATE_FILE -> 6\n    ScanItemKind.PROJECT_OLD_VERSION -> 7\n    ScanItemKind.PROJECT_EXPORT -> 8\n    ScanItemKind.PROJECT_ARCHIVE -> 9\n    ScanItemKind.PROJECT_TEMPORARY -> 10\n",
        "    ScanItemKind.APP_LEFTOVER -> 0\n    ScanItemKind.CACHE_OR_TEMP -> 1\n    ScanItemKind.OLD_DOWNLOAD -> 2\n    ScanItemKind.OLD_SCREENSHOT -> 3\n    ScanItemKind.APK_OR_ZIP -> 4\n    ScanItemKind.LARGE_FILE -> 5\n    ScanItemKind.EMPTY_FOLDER -> 6\n    ScanItemKind.DUPLICATE_FILE -> 7\n    ScanItemKind.PROJECT_OLD_VERSION -> 8\n    ScanItemKind.PROJECT_EXPORT -> 9\n    ScanItemKind.PROJECT_ARCHIVE -> 10\n    ScanItemKind.PROJECT_TEMPORARY -> 11\n",
        1,
    )
if 'ScanItemKind.CACHE_OR_TEMP -> "CACHE / TEMP · manual selection · verified after delete"' not in r:
    r = r.replace('    ScanItemKind.APP_LEFTOVER -> "POSSIBLE APP LEFTOVER · manual selection"\n', '    ScanItemKind.APP_LEFTOVER -> "POSSIBLE APP LEFTOVER · manual selection"\n    ScanItemKind.CACHE_OR_TEMP -> "CACHE / TEMP · manual selection · verified after delete"\n', 1)
r = r.replace("BUILD 0.10.4-phase10p4 • VERIFIED FOLDER DELETE", "BUILD 0.10.5-phase10p5 • VERIFIED CACHE CLEANUP")
review.write_text(r)

rs = result_screen.read_text()
rs = rs.replace(
    "            if (item.kind == ScanItemKind.OLD_DOWNLOAD || item.kind == ScanItemKind.OLD_SCREENSHOT) {",
    "            if (item.kind == ScanItemKind.OLD_DOWNLOAD || item.kind == ScanItemKind.OLD_SCREENSHOT || item.kind == ScanItemKind.CACHE_OR_TEMP) {",
    1,
)
app_ui = """            if (item.kind == ScanItemKind.APP_LEFTOVER) {
                val score = item.leftoverConfidenceScore ?: 0
                Text(
                    "\${OrphanRules.confidenceLabel(score)} confidence · $score/100 · \${item.leftoverPackageName ?: "unknown package"}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.tertiary,
                )
                item.leftoverReasons.take(2).forEach { reason ->
                    Text(
                        "• $reason",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
"""
cache_result_ui = """            if (item.kind == ScanItemKind.CACHE_OR_TEMP) {
                Text(
                    "CACHE/TEMP confidence · \${item.cacheConfidenceScore ?: 0}/100",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.tertiary,
                )
                item.cacheReason?.let { reason ->
                    Text(
                        "• $reason",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
"""
if "CACHE/TEMP confidence" not in rs:
    if app_ui not in rs:
        raise SystemExit("Result APP_LEFTOVER UI marker missing")
    rs = rs.replace(app_ui, app_ui + cache_result_ui, 1)
result_screen.write_text(rs)

e = engine.read_text()
generic_success = """                result.isSuccess && result.getOrDefault(false) -> CleanupItemResult(
                    item = currentItem,
                    status = CleanupStatus.SUCCESS,
                )
"""
cache_success = """                result.isSuccess && result.getOrDefault(false) && currentItem.kind == ScanItemKind.CACHE_OR_TEMP -> {
                    when (verifyCacheFileDeleted(itemUri)) {
                        DocumentPresence.ABSENT -> CleanupItemResult(
                            item = currentItem,
                            status = CleanupStatus.SUCCESS,
                            message = "ยืนยันแล้วว่า cache/temp file ถูกลบออกจาก storage จริง",
                        )
                        DocumentPresence.PRESENT -> CleanupItemResult(
                            item = currentItem,
                            status = CleanupStatus.FAILED,
                            message = "Document provider ตอบว่าลบแล้ว แต่ตรวจซ้ำพบว่า cache/temp file ยังอยู่",
                        )
                        DocumentPresence.UNKNOWN -> CleanupItemResult(
                            item = currentItem,
                            status = CleanupStatus.FAILED,
                            message = "ส่งคำสั่งลบ cache/temp แล้ว แต่ยืนยันไม่ได้ว่าไฟล์หายจริง กรุณา Full Scan",
                        )
                    }
                }

"""
if "verifyCacheFileDeleted(itemUri)" not in e:
    if generic_success not in e:
        raise SystemExit("generic delete SUCCESS marker missing")
    e = e.replace(generic_success, cache_success + generic_success, 1)
folder_helper = "    private suspend fun verifyFolderDeleted(uri: Uri): DocumentPresence {\n"
cache_helper = """    private suspend fun verifyCacheFileDeleted(uri: Uri): DocumentPresence {
        var latest = queryDocumentPresence(uri)
        repeat(FOLDER_DELETE_VERIFY_RETRIES - 1) {
            if (latest == DocumentPresence.ABSENT) return latest
            delay(FOLDER_DELETE_VERIFY_DELAY_MS)
            latest = queryDocumentPresence(uri)
        }
        return latest
    }

"""
if "private suspend fun verifyCacheFileDeleted" not in e:
    if folder_helper not in e:
        raise SystemExit("verifyFolderDeleted helper marker missing")
    e = e.replace(folder_helper, cache_helper + folder_helper, 1)
engine.write_text(e)

cache_test.parent.mkdir(parents=True, exist_ok=True)
cache_test.write_text(r'''package com.soloforge.soloclean.scanner

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.TimeUnit

class CacheRulesTest {
    private val now = 2_000_000_000_000L

    @Test fun oldFileInsideCacheDirectoryIsCandidate() {
        val match = CacheRules.classify("SomeApp/cache/image.bin", "image.bin", now - TimeUnit.DAYS.toMillis(30), now)
        assertEquals(85, match?.confidenceScore)
        assertTrue(match?.reason?.contains("cache") == true)
    }

    @Test fun recentCacheFileIsNotCandidate() {
        assertNull(CacheRules.classify("SomeApp/cache/image.bin", "image.bin", now - TimeUnit.DAYS.toMillis(1), now))
    }

    @Test fun unrelatedOldFileIsNotCandidate() {
        assertNull(CacheRules.classify("Documents/report.pdf", "report.pdf", now - TimeUnit.DAYS.toMillis(100), now))
    }

    @Test fun oldTmpExtensionIsManualCandidate() {
        assertEquals(70, CacheRules.classify("Download/export.tmp", "export.tmp", now - TimeUnit.DAYS.toMillis(10), now)?.confidenceScore)
    }

    @Test fun metadataRequiresAgeConfidenceAndReason() {
        assertTrue(CacheRules.isSupportedCandidateMetadata(7, 70, "temporary extension"))
        assertTrue(!CacheRules.isSupportedCandidateMetadata(1, 85, "cache folder"))
        assertTrue(!CacheRules.isSupportedCandidateMetadata(7, 50, "weak"))
        assertTrue(!CacheRules.isSupportedCandidateMetadata(7, 85, null))
    }
}
''')

g = gradle.read_text()
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 20', g, count=1)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.10.5-phase10p5"', g, count=1)
gradle.write_text(g)
for pth in root.rglob("*.kt"):
    x = pth.read_text().replace("0.10.4-phase10p4", "0.10.5-phase10p5")
    pth.write_text(x)

assert "CACHE_OR_TEMP" in model.read_text()
assert "CacheRules.classify(" in scanner.read_text()
assert 'title = "Cache & temporary files"' in scanner.read_text()
assert "ScanItemKind.CACHE_OR_TEMP ->" in policy.read_text()
assert "verifyCacheFileDeleted(itemUri)" in engine.read_text()
assert "CACHE / TEMP · manual selection · verified after delete" in review.read_text()
assert 'versionName = "0.10.5-phase10p5"' in gradle.read_text()

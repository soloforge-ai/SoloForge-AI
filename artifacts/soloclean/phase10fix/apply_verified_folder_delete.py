from pathlib import Path
import re

root = Path("soloclean/app/src/main/java/com/soloforge/soloclean")
engine = root / "cleanup/AndroidSafCleanupEngine.kt"
scanner = root / "scanner/AndroidReadOnlyScanEngine.kt"
model = root / "data/model/ScanItem.kt"
review = root / "ui/review/ReviewScreen.kt"
gradle = Path("soloclean/app/build.gradle.kts")

# 1) Model: preserve whether an empty-folder candidate is directly empty or an empty tree.
m = model.read_text()
if "enum class EmptyFolderState" not in m:
    marker = "enum class ScanItemKind {"
    enum_text = """enum class EmptyFolderState {
    TRULY_EMPTY,
    CONTAINS_ONLY_EMPTY_SUBFOLDERS,
}

"""
    if marker not in m:
        raise SystemExit("ScanItemKind marker missing")
    m = m.replace(marker, enum_text + marker, 1)

field_marker = "    val isDirectory: Boolean = false,\n"
field_text = "    val emptyFolderState: EmptyFolderState? = null,\n"
if field_text not in m:
    if field_marker not in m:
        raise SystemExit("ScanItem isDirectory field missing")
    m = m.replace(field_marker, field_marker + field_text, 1)
model.write_text(m)

# 2) Scanner: classify direct-empty vs contains-only-empty-subfolders.
s = scanner.read_text()
if "import com.soloforge.soloclean.data.model.EmptyFolderState" not in s:
    import_marker = "import com.soloforge.soloclean.data.model."
    first = s.find(import_marker)
    if first < 0:
        raise SystemExit("scanner model import marker missing")
    line_end = s.find("\n", first)
    s = s[:line_end+1] + "import com.soloforge.soloclean.data.model.EmptyFolderState\n" + s[line_end+1:]

old_empty = """        if (!isRoot && !containsAnyFile) {
            accumulator.emptyFolders += ScanItem(
                uri = directory.uri.toString(),
                name = directory.name?.takeIf { it.isNotBlank() } ?: "Unnamed folder",
                relativePath = relativePath,
                sizeBytes = 0L,
                lastModifiedMillis = directory.lastModified().coerceAtLeast(0L),
                kind = ScanItemKind.EMPTY_FOLDER,
                isDirectory = true,
            )
        }
"""
new_empty = """        if (!isRoot && !containsAnyFile) {
            accumulator.emptyFolders += ScanItem(
                uri = directory.uri.toString(),
                name = directory.name?.takeIf { it.isNotBlank() } ?: "Unnamed folder",
                relativePath = relativePath,
                sizeBytes = 0L,
                lastModifiedMillis = directory.lastModified().coerceAtLeast(0L),
                kind = ScanItemKind.EMPTY_FOLDER,
                isDirectory = true,
                emptyFolderState = if (children.isEmpty()) {
                    EmptyFolderState.TRULY_EMPTY
                } else {
                    EmptyFolderState.CONTAINS_ONLY_EMPTY_SUBFOLDERS
                },
            )
        }
"""
if "emptyFolderState = if (children.isEmpty())" not in s:
    if old_empty not in s:
        raise SystemExit("empty folder creation block missing")
    s = s.replace(old_empty, new_empty, 1)

s = s.replace(
    'subtitle = "โฟลเดอร์ที่ไม่มีไฟล์อยู่ภายในทุกระดับ",',
    'subtitle = "แยกโฟลเดอร์ว่างจริงออกจากโฟลเดอร์ที่มีแต่โฟลเดอร์ย่อยว่าง — ลบจากชั้นลึกขึ้นมาก่อน",',
)
scanner.write_text(s)

# 3) Cleanup: verify an EMPTY_FOLDER is actually gone before reporting SUCCESS.
e = engine.read_text()
if "import kotlinx.coroutines.delay" not in e:
    e = e.replace("import kotlinx.coroutines.Dispatchers\n", "import kotlinx.coroutines.Dispatchers\nimport kotlinx.coroutines.delay\n", 1)
if "import java.io.FileNotFoundException" not in e:
    e = e.replace("import java.security.MessageDigest\n", "import java.io.FileNotFoundException\nimport java.security.MessageDigest\n", 1)

old_delete = """            val result = runCatching { DocumentsContract.deleteDocument(resolver, itemUri) }
            results += when {
                result.isSuccess && result.getOrDefault(false) -> CleanupItemResult(
                    item = currentItem,
                    status = CleanupStatus.SUCCESS,
                )

                result.exceptionOrNull() is SecurityException -> CleanupItemResult(
"""
new_delete = """            val result = runCatching { DocumentsContract.deleteDocument(resolver, itemUri) }
            results += when {
                result.isSuccess && result.getOrDefault(false) && currentItem.kind == ScanItemKind.EMPTY_FOLDER -> {
                    when (verifyFolderDeleted(itemUri)) {
                        DocumentPresence.ABSENT -> CleanupItemResult(
                            item = currentItem,
                            status = CleanupStatus.SUCCESS,
                            message = "ยืนยันแล้วว่าโฟลเดอร์ถูกลบออกจาก storage จริง",
                        )
                        DocumentPresence.PRESENT -> CleanupItemResult(
                            item = currentItem,
                            status = CleanupStatus.FAILED,
                            message = "Document provider ตอบว่าลบแล้ว แต่ตรวจซ้ำพบว่าโฟลเดอร์ยังอยู่ จึงไม่นับเป็น Success",
                        )
                        DocumentPresence.UNKNOWN -> CleanupItemResult(
                            item = currentItem,
                            status = CleanupStatus.FAILED,
                            message = "ส่งคำสั่งลบแล้ว แต่ยืนยันไม่ได้ว่าโฟลเดอร์หายจริง กรุณา Full Scan ก่อนลองใหม่",
                        )
                    }
                }

                result.isSuccess && result.getOrDefault(false) -> CleanupItemResult(
                    item = currentItem,
                    status = CleanupStatus.SUCCESS,
                )

                result.exceptionOrNull() is SecurityException -> CleanupItemResult(
"""
if "verifyFolderDeleted(itemUri)" not in e:
    if old_delete not in e:
        raise SystemExit("delete result block missing")
    e = e.replace(old_delete, new_delete, 1)

helper_marker = """    private fun isStillEmptyDirectory(document: DocumentFile): Boolean {
"""
helper = """    private suspend fun verifyFolderDeleted(uri: Uri): DocumentPresence {
        var latest = queryDocumentPresence(uri)
        repeat(FOLDER_DELETE_VERIFY_RETRIES - 1) {
            if (latest == DocumentPresence.ABSENT) return latest
            delay(FOLDER_DELETE_VERIFY_DELAY_MS)
            latest = queryDocumentPresence(uri)
        }
        return latest
    }

    private fun queryDocumentPresence(uri: Uri): DocumentPresence = try {
        resolver.query(
            uri,
            arrayOf(DocumentsContract.Document.COLUMN_DOCUMENT_ID),
            null,
            null,
            null,
        )?.use { cursor ->
            if (cursor.moveToFirst()) DocumentPresence.PRESENT else DocumentPresence.ABSENT
        } ?: DocumentPresence.UNKNOWN
    } catch (_: FileNotFoundException) {
        DocumentPresence.ABSENT
    } catch (_: SecurityException) {
        DocumentPresence.UNKNOWN
    } catch (_: IllegalArgumentException) {
        DocumentPresence.UNKNOWN
    } catch (_: UnsupportedOperationException) {
        DocumentPresence.UNKNOWN
    }

"""
if "private suspend fun verifyFolderDeleted" not in e:
    if helper_marker not in e:
        raise SystemExit("isStillEmptyDirectory marker missing")
    e = e.replace(helper_marker, helper + helper_marker, 1)

companion_marker = """    private companion object {
        const val HASH_BUFFER_SIZE = 256 * 1024
"""
companion_new = """    private companion object {
        const val HASH_BUFFER_SIZE = 256 * 1024
        const val FOLDER_DELETE_VERIFY_RETRIES = 3
        const val FOLDER_DELETE_VERIFY_DELAY_MS = 100L
"""
if "FOLDER_DELETE_VERIFY_RETRIES" not in e:
    if companion_marker not in e:
        raise SystemExit("companion marker missing")
    e = e.replace(companion_marker, companion_new, 1)

hash_marker = """    private data class HashSnapshot(
        val sha256: String,
        val bytesRead: Long,
    )

"""
presence_enum = """    private enum class DocumentPresence {
        PRESENT,
        ABSENT,
        UNKNOWN,
    }

"""
if "private enum class DocumentPresence" not in e:
    if hash_marker not in e:
        raise SystemExit("HashSnapshot marker missing")
    e = e.replace(hash_marker, hash_marker + presence_enum, 1)

engine.write_text(e)

# 4) Review UI: make empty-folder shape explicit and stamp the QA build.
r = review.read_text()
if "import com.soloforge.soloclean.data.model.EmptyFolderState" not in r:
    import_scan = "import com.soloforge.soloclean.data.model.ScanItem\n"
    if import_scan not in r:
        raise SystemExit("Review ScanItem import missing")
    r = r.replace(import_scan, "import com.soloforge.soloclean.data.model.EmptyFolderState\n" + import_scan, 1)

r = r.replace("                    item.kind.reviewLabel(),", "                    item.reviewLabel(),", 1)

old_fun = """private fun ScanItemKind.reviewLabel(): String = when (this) {
    ScanItemKind.EMPTY_FOLDER -> "EMPTY FOLDER · manual selection"
"""
new_fun = """private fun ScanItem.reviewLabel(): String = when (kind) {
    ScanItemKind.EMPTY_FOLDER -> when (emptyFolderState) {
        EmptyFolderState.TRULY_EMPTY -> "TRULY EMPTY FOLDER · verified direct-empty at scan"
        EmptyFolderState.CONTAINS_ONLY_EMPTY_SUBFOLDERS -> "EMPTY TREE · contains only empty subfolders · deepest folders delete first"
        null -> "EMPTY FOLDER · legacy candidate · rechecked before delete"
    }
"""
if "private fun ScanItem.reviewLabel()" not in r:
    if old_fun not in r:
        raise SystemExit("reviewLabel function missing")
    r = r.replace(old_fun, new_fun, 1)

header = '                Text(\n                    "Review cleanup",\n                    style = MaterialTheme.typography.headlineMedium,\n                    fontWeight = FontWeight.Bold,\n                )\n'
stamp = '                Text("BUILD 0.10.4-phase10p4 • VERIFIED FOLDER DELETE", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)\n'
if "VERIFIED FOLDER DELETE" not in r:
    if header not in r:
        raise SystemExit("Review header missing")
    r = r.replace(header, header + stamp, 1)
review.write_text(r)

# 5) Version and visible version stamps.
g = gradle.read_text()
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 19', g, count=1)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.10.4-phase10p4"', g, count=1)
gradle.write_text(g)

for p in root.rglob("*.kt"):
    x = p.read_text()
    x = x.replace("0.10.3-phase10p3", "0.10.4-phase10p4")
    p.write_text(x)

# Hard gates.
assert "verifyFolderDeleted(itemUri)" in engine.read_text()
assert "DocumentPresence.PRESENT" in engine.read_text()
assert "emptyFolderState = if (children.isEmpty())" in scanner.read_text()
assert "TRULY EMPTY FOLDER" in review.read_text()
assert "EMPTY TREE" in review.read_text()
assert "VERIFIED FOLDER DELETE" in review.read_text()
assert 'versionName = "0.10.4-phase10p4"' in gradle.read_text()

package com.soloforge.soloclean

import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.tooling.preview.Preview
import com.soloforge.soloclean.cleanup.AndroidSafCleanupEngine
import com.soloforge.soloclean.cleanup.CleanupEngine
import com.soloforge.soloclean.data.model.ScanSummary
import com.soloforge.soloclean.data.model.StorageAccessState
import com.soloforge.soloclean.data.model.StorageSnapshot
import com.soloforge.soloclean.data.repository.AndroidStorageRepository
import com.soloforge.soloclean.data.repository.StorageRepository
import com.soloforge.soloclean.permission.StoragePermissionManager
import com.soloforge.soloclean.scanner.AndroidReadOnlyScanEngine
import com.soloforge.soloclean.scanner.ScanEngine
import com.soloforge.soloclean.ui.home.HomeScreen
import com.soloforge.soloclean.ui.result.ResultScreen
import com.soloforge.soloclean.ui.review.ReviewScreen
import com.soloforge.soloclean.ui.scan.ScanScreen
import com.soloforge.soloclean.ui.theme.SoloCleanTheme

private enum class SoloCleanScreen {
    Home,
    Scan,
    Result,
    Review,
}

class MainActivity : ComponentActivity() {
    private lateinit var storageRepository: StorageRepository
    private lateinit var storagePermissionManager: StoragePermissionManager
    private lateinit var scanEngine: ScanEngine
    private lateinit var cleanupEngine: CleanupEngine

    private var storageSnapshot by mutableStateOf(StorageSnapshot.Empty)
    private var storageAccess by mutableStateOf(StorageAccessState.NotGranted)
    private var storageAccessError by mutableStateOf<String?>(null)

    private val openDocumentTree = registerForActivityResult(
        ActivityResultContracts.OpenDocumentTree(),
    ) { uri: Uri? ->
        if (uri == null) return@registerForActivityResult

        runCatching {
            storagePermissionManager.persistTreeAccess(uri)
        }.onSuccess { access ->
            storageAccess = access
            storageAccessError = null
        }.onFailure {
            storageAccess = storagePermissionManager.currentAccess()
            storageAccessError = "ไม่สามารถบันทึกสิทธิ์โฟลเดอร์นี้ได้ กรุณาเลือกโฟลเดอร์อื่น"
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        storageRepository = AndroidStorageRepository(applicationContext)
        storagePermissionManager = StoragePermissionManager(applicationContext)
        scanEngine = AndroidReadOnlyScanEngine(applicationContext)
        cleanupEngine = AndroidSafCleanupEngine(applicationContext)
        refreshStorageState()

        setContent {
            SoloCleanTheme {
                SoloCleanApp(
                    storageSnapshot = storageSnapshot,
                    storageAccess = storageAccess,
                    storageAccessError = storageAccessError,
                    scanEngine = scanEngine,
                    cleanupEngine = cleanupEngine,
                    onChooseFolder = {
                        storageAccessError = null
                        openDocumentTree.launch(storageAccess.treeUri)
                    },
                    onClearFolderAccess = {
                        storagePermissionManager.clearCurrentAccess()
                        storageAccess = StorageAccessState.NotGranted
                        storageAccessError = null
                    },
                    onRefreshStorage = ::refreshStorageState,
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        if (::storageRepository.isInitialized && ::storagePermissionManager.isInitialized) {
            refreshStorageState()
        }
    }

    private fun refreshStorageState() {
        storageSnapshot = runCatching {
            storageRepository.getPrimaryStorageSnapshot()
        }.getOrDefault(StorageSnapshot.Empty)

        storageAccess = storagePermissionManager.currentAccess()
    }
}

@Composable
private fun SoloCleanApp(
    storageSnapshot: StorageSnapshot,
    storageAccess: StorageAccessState,
    storageAccessError: String?,
    scanEngine: ScanEngine,
    cleanupEngine: CleanupEngine,
    onChooseFolder: () -> Unit,
    onClearFolderAccess: () -> Unit,
    onRefreshStorage: () -> Unit,
) {
    var screen by androidx.compose.runtime.remember {
        mutableStateOf(SoloCleanScreen.Home)
    }
    var latestScanSummary by androidx.compose.runtime.remember {
        mutableStateOf<ScanSummary?>(null)
    }

    when (screen) {
        SoloCleanScreen.Home -> HomeScreen(
            storageSnapshot = storageSnapshot,
            storageAccess = storageAccess,
            storageAccessError = storageAccessError,
            latestScanSummary = latestScanSummary,
            onChooseFolder = onChooseFolder,
            onClearFolderAccess = onClearFolderAccess,
            onScanNow = { screen = SoloCleanScreen.Scan },
        )

        SoloCleanScreen.Scan -> ScanScreen(
            treeUri = storageAccess.treeUri,
            folderName = storageAccess.displayName,
            scanEngine = scanEngine,
            onScanCompleted = { summary ->
                latestScanSummary = summary
                screen = SoloCleanScreen.Result
            },
            onBackHome = { screen = SoloCleanScreen.Home },
        )

        SoloCleanScreen.Result -> ResultScreen(
            summary = latestScanSummary ?: ScanSummary.Empty,
            canWrite = storageAccess.canWrite,
            onReviewCleanup = { screen = SoloCleanScreen.Review },
            onBackHome = { screen = SoloCleanScreen.Home },
            onScanAgain = { screen = SoloCleanScreen.Scan },
        )

        SoloCleanScreen.Review -> ReviewScreen(
            summary = latestScanSummary ?: ScanSummary.Empty,
            treeUri = storageAccess.treeUri,
            canWrite = storageAccess.canWrite,
            cleanupEngine = cleanupEngine,
            onBack = { screen = SoloCleanScreen.Result },
            onFullScan = { screen = SoloCleanScreen.Scan },
            onSessionStorageChanged = onRefreshStorage,
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun SoloCleanPreview() {
    SoloCleanTheme {
        HomeScreen(
            storageSnapshot = StorageSnapshot(
                totalBytes = 128L * 1024 * 1024 * 1024,
                availableBytes = 36L * 1024 * 1024 * 1024,
            ),
            storageAccess = StorageAccessState.NotGranted,
            storageAccessError = null,
            latestScanSummary = null,
            onChooseFolder = {},
            onClearFolderAccess = {},
            onScanNow = {},
        )
    }
}

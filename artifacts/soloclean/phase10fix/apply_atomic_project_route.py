from pathlib import Path

main = Path('soloclean/app/src/main/java/com/soloforge/soloclean/MainActivity.kt')
s = main.read_text()

old_enum = '''private enum class SoloCleanScreen {\n    Home,\n    Scan,\n    Result,\n    Review,\n    Projects,\n    ProjectCleanup,\n}\n'''
new_route = '''private sealed interface SoloCleanRoute {\n    data object Home : SoloCleanRoute\n    data object Scan : SoloCleanRoute\n    data object Result : SoloCleanRoute\n    data object Review : SoloCleanRoute\n    data object Projects : SoloCleanRoute\n    data class ProjectCleanup(val projectId: String) : SoloCleanRoute\n}\n'''
if old_enum not in s:
    raise SystemExit('Expected SoloCleanScreen enum not found')
s = s.replace(old_enum, new_route, 1)

old_state = '''    var screen by androidx.compose.runtime.remember { mutableStateOf(SoloCleanScreen.Home) }\n    var latestScanSummary by androidx.compose.runtime.remember { mutableStateOf<ScanSummary?>(null) }\n    var selectedProjectId by androidx.compose.runtime.remember { mutableStateOf<String?>(null) }\n\n    when (screen) {\n        SoloCleanScreen.Home -> HomeScreen('''
new_state = '''    var route by androidx.compose.runtime.remember { mutableStateOf<SoloCleanRoute>(SoloCleanRoute.Home) }\n    var latestScanSummary by androidx.compose.runtime.remember { mutableStateOf<ScanSummary?>(null) }\n\n    when (val currentRoute = route) {\n        SoloCleanRoute.Home -> HomeScreen('''
if old_state not in s:
    raise SystemExit('Expected split navigation state not found')
s = s.replace(old_state, new_state, 1)

replacements = {
    'screen = SoloCleanScreen.Scan': 'route = SoloCleanRoute.Scan',
    'screen = SoloCleanScreen.Home': 'route = SoloCleanRoute.Home',
    'screen = SoloCleanScreen.Result': 'route = SoloCleanRoute.Result',
    'screen = SoloCleanScreen.Review': 'route = SoloCleanRoute.Review',
    'screen = SoloCleanScreen.Projects': 'route = SoloCleanRoute.Projects',
    'SoloCleanScreen.Scan ->': 'SoloCleanRoute.Scan ->',
    'SoloCleanScreen.Result ->': 'SoloCleanRoute.Result ->',
    'SoloCleanScreen.Review ->': 'SoloCleanRoute.Review ->',
    'SoloCleanScreen.Projects ->': 'SoloCleanRoute.Projects ->',
}
for old, new in replacements.items():
    s = s.replace(old, new)

old_click = '''            onProjectCleanup = { projectId ->\n                selectedProjectId = projectId\n                screen = SoloCleanScreen.ProjectCleanup\n            },'''
new_click = '''            onProjectCleanup = { projectId ->\n                route = SoloCleanRoute.ProjectCleanup(projectId)\n            },'''
if old_click not in s:
    raise SystemExit('Expected project cleanup click wiring not found')
s = s.replace(old_click, new_click, 1)

old_branch = '''        SoloCleanScreen.ProjectCleanup -> {\n            val summary = latestScanSummary ?: ScanSummary.Empty\n            val projectAnalysis = projectFingerprintEngine\n                .analyze(summary.files, projects, projectDecisions)\n                .firstOrNull { it.project.id == selectedProjectId }\n            if (projectAnalysis == null) {\n                selectedProjectId = null\n                route = SoloCleanRoute.Projects\n            } else {'''
new_branch = '''        is SoloCleanRoute.ProjectCleanup -> {\n            val summary = latestScanSummary ?: ScanSummary.Empty\n            val projectAnalysis = projectFingerprintEngine\n                .analyze(summary.files, projects, projectDecisions)\n                .firstOrNull { it.project.id == currentRoute.projectId }\n            if (projectAnalysis == null) {\n                route = SoloCleanRoute.Projects\n            } else {'''
if old_branch not in s:
    raise SystemExit('Expected project cleanup route branch not found')
s = s.replace(old_branch, new_branch, 1)

if 'SoloCleanScreen' in s or 'selectedProjectId' in s or 'screen =' in s:
    raise SystemExit('Split navigation state still present after route patch')
if 'data class ProjectCleanup(val projectId: String)' not in s:
    raise SystemExit('Atomic ProjectCleanup route missing')
if 'route = SoloCleanRoute.ProjectCleanup(projectId)' not in s:
    raise SystemExit('Project cleanup button is not wired to atomic route')

main.write_text(s)

cleanup = Path('soloclean/app/src/main/java/com/soloforge/soloclean/ui/projectcleanup/ProjectCleanupScreen.kt')
c = cleanup.read_text()
c = c.replace('BUILD 0.10.0-phase10 • PROJECT CLEANUP', 'BUILD 0.10.2-phase10p2 • PROJECT ROUTE ACTIVE')
cleanup.write_text(c)

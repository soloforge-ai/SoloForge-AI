"""Normalize SoloForge operational webhook events into a small stable contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEFAULT_REPOSITORY = "soloforge-ai/SoloForge-AI"


@dataclass(frozen=True)
class OpsEvent:
    event_key: str
    category: str
    event_type: str
    severity: str
    source: str
    subject: str
    status: str
    commit_sha: str | None = None
    details: dict[str, object] = field(default_factory=dict)


def _repo_full_name(payload: dict[str, Any]) -> str:
    repository = payload.get("repository") or {}
    return str(repository.get("full_name") or "")


def _workflow_subject(payload: dict[str, Any]) -> str:
    job = payload.get("workflow_job") or {}
    return str(job.get("workflow_name") or job.get("name") or "GitHub Actions")


def _commit_sha(payload: dict[str, Any]) -> str | None:
    job = payload.get("workflow_job") or {}
    sha = job.get("head_sha")
    if sha:
        return str(sha)
    run = payload.get("workflow_run") or {}
    sha = run.get("head_sha")
    return str(sha) if sha else None


def _job_started(job: dict[str, Any]) -> bool:
    if str(job.get("runner_name") or "").strip():
        return True
    if job.get("started_at"):
        return True
    for step in job.get("steps") or []:
        if step.get("started_at") or step.get("completed_at"):
            return True
        if str(step.get("status") or "") in {"in_progress", "completed"}:
            return True
    return False


def normalize_github_event(
    event_name: str,
    delivery_id: str,
    payload: dict[str, Any],
    *,
    repository: str = DEFAULT_REPOSITORY,
) -> OpsEvent | None:
    if _repo_full_name(payload) != repository:
        return None

    if event_name == "pull_request":
        action = str(payload.get("action") or "")
        pr = payload.get("pull_request") or {}
        if action != "closed" or not bool(pr.get("merged")):
            return None
        number = pr.get("number") or payload.get("number")
        merge_sha = str(pr.get("merge_commit_sha") or "") or None
        title = str(pr.get("title") or f"PR #{number}")
        return OpsEvent(
            event_key=f"github:pull_request:{number}:merged:{merge_sha or delivery_id}",
            category="GIT",
            event_type="pull_request.merged",
            severity="info",
            source="github",
            subject=f"PR #{number} {title}",
            status="MERGED",
            commit_sha=merge_sha,
            details={"number": number, "url": pr.get("html_url")},
        )

    if event_name != "workflow_job":
        return None

    if str(payload.get("action") or "") != "completed":
        return None

    job = payload.get("workflow_job") or {}
    job_id = job.get("id")
    run_id = job.get("run_id")
    conclusion = str(job.get("conclusion") or "").lower()
    job_name = str(job.get("name") or "workflow-job")
    subject = _workflow_subject(payload)
    sha = _commit_sha(payload)
    started = _job_started(job)
    is_smoke = "production-smoke" in job_name.lower() or "production smoke" in subject.lower()

    common_details: dict[str, object] = {
        "job_id": job_id,
        "run_id": run_id,
        "job_name": job_name,
        "workflow_name": subject,
        "runner_name": job.get("runner_name"),
        "runner_group_name": job.get("runner_group_name"),
        "started": started,
        "html_url": job.get("html_url"),
    }

    if conclusion == "cancelled" and not started:
        return OpsEvent(
            event_key=f"github:workflow_job:{job_id}:runner_unavailable",
            category="CI",
            event_type="runner.unavailable",
            severity="warning",
            source="github",
            subject=subject,
            status="INFRA",
            commit_sha=sha,
            details=common_details,
        )

    if conclusion == "cancelled":
        return OpsEvent(
            event_key=f"github:workflow_job:{job_id}:cancelled",
            category="CI",
            event_type="workflow.cancelled",
            severity="warning",
            source="github",
            subject=subject,
            status="CANCELLED",
            commit_sha=sha,
            details=common_details,
        )

    if is_smoke and conclusion in {"success", "failure"}:
        passed = conclusion == "success"
        return OpsEvent(
            # GitHub may emit duplicate workflow runs for the same push. Use the
            # logical production-smoke result as the idempotency key so duplicate
            # runs for the same commit/conclusion enqueue only one notification.
            event_key=f"github:production_smoke:{sha or 'unknown'}:{conclusion}",
            category="SMK",
            event_type=f"production_smoke.{'passed' if passed else 'failed'}",
            severity="info" if passed else "error",
            source="github",
            subject=subject,
            status="SUCCESS" if passed else "FAILURE",
            commit_sha=sha,
            details=common_details,
        )

    if conclusion in {"success", "failure"}:
        passed = conclusion == "success"
        return OpsEvent(
            event_key=f"github:workflow_job:{job_id}:ci:{conclusion}",
            category="CI",
            event_type=f"ci.{'passed' if passed else 'failed'}",
            severity="info" if passed else "error",
            source="github",
            subject=subject,
            status="SUCCESS" if passed else "FAILURE",
            commit_sha=sha,
            details=common_details,
        )

    return None


def event_code(category: str, notification_id: int) -> str:
    return f"SF-{category}-{notification_id:03d}"


def format_telegram_message(event: OpsEvent, notification_id: int) -> str:
    code = event_code(event.category, notification_id)
    sha = (event.commit_sha or "-")[:8]
    job_name = str(event.details.get("job_name") or "-")

    if event.event_type == "runner.unavailable":
        return (
            f"[{code}] ⚠️ GITHUB RUNNER UNAVAILABLE\n\n"
            f"Workflow: {event.subject}\n"
            f"Job: {job_name}\n"
            f"Commit: {sha}\n"
            "Execution: NOT STARTED\n"
            "Production Status: UNKNOWN\n\n"
            "Reason:\n"
            "GitHub-hosted runner did not acquire the job before it was cancelled.\n\n"
            "Action:\nRetry when GitHub-hosted runners recover."
        )

    icon = "✅" if event.severity == "info" else "❌" if event.severity == "error" else "⚠️"
    title = event.event_type.replace("_", " ").replace(".", " ").upper()
    lines = [
        f"[{code}] {icon} {title}",
        "",
        f"Subject: {event.subject}",
        f"Status: {event.status}",
        f"Commit: {sha}",
    ]
    if job_name != "-":
        lines.append(f"Job: {job_name}")
    return "\n".join(lines)

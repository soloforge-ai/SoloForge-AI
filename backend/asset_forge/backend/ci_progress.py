"""Optional bounded progress lookup; failure notifications never call this."""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request

REPOSITORY = "soloforge-ai/SoloForge-AI"
API_TIMEOUT_SECONDS = 0.4


def confirmed_progress(event, *, fetch=None):
    """Return (ordinal, total) only for a complete multi-job run attempt."""
    if event.category != "CI" or event.event_type != "ci.passed":
        return None
    job_id, run_id = event.details.get("job_id"), event.details.get("run_id")
    if type(job_id) is not int or type(run_id) is not int or not event.commit_sha:
        return None

    def request(path):
        token = os.getenv("GITHUB_OPS_API_TOKEN", "").strip()
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "SoloForge-Ops"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request("https://api.github.com/repos/" + REPOSITORY + path, headers=headers)
        with urllib.request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as response:
            return json.load(response)

    get = fetch or request
    try:
        run = get(f"/actions/runs/{run_id}")
        if run.get("status") != "completed" or run.get("head_sha") != event.commit_sha:
            return None
        attempt = run.get("run_attempt")
        if type(attempt) is not int or attempt < 1:
            return None
        payload = get(f"/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100")
        jobs = payload.get("jobs")
        if (not isinstance(jobs, list) or not 1 < len(jobs) <= 100
                or payload.get("total_count") != len(jobs)):
            return None
        if any(not isinstance(j, dict) or j.get("status") != "completed"
               or not j.get("completed_at") or type(j.get("id")) is not int
               or j.get("run_attempt") != attempt for j in jobs):
            return None
        if len({j["id"] for j in jobs}) != len(jobs):
            return None
        ordered = sorted(jobs, key=lambda j: (j["completed_at"], j["id"]))
        indices = [i for i, j in enumerate(ordered, 1) if j["id"] == job_id]
        return (indices[0], len(jobs)) if len(indices) == 1 else None
    except (urllib.error.URLError, OSError, TimeoutError, ValueError, TypeError, KeyError, AttributeError):
        return None

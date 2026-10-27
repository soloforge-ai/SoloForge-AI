"""Tenant-scoped adapters for the retained Pollinations and Content Job tables."""
from datetime import datetime
import hashlib
from io import BytesIO
from pathlib import Path
import secrets
from tempfile import TemporaryDirectory
from uuid import UUID
import wave
from fastapi import HTTPException
from .shared_supabase import supabase_request
from .byop_ledger import digest


def record_id(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError):
        raise HTTPException(400, "Record UUID required") from None


def rpc(name, **params):
    try:
        return supabase_request("POST", "rpc/byop_" + name, params)
    except Exception:
        # Never echo a key, provider payload or SQL error. Lost responses are
        # ambiguous mutations: no transport retry or automatic dispatch follows.
        raise HTTPException(503, "BYOP persistence unavailable or outcome unconfirmed") from None


def job_record(row):
    if not row:
        raise HTTPException(404, "Content Job unavailable")
    return {**row, "principal": row["byop_principal"], "revision": row["byop_revision"],
            "model": row["byop_model"]}


class Repository:
    def credentials(self, principal):
        return rpc("credentials", p_principal=principal)

    def credential(self, principal, credential_id):
        row = rpc("credential", p_principal=principal, p_id=record_id(credential_id))
        if not row:
            return None
        return {"principal": principal, "token": row["access_token"],
                "provider_subject": row.get("provider_subject"),
                "expires_at": datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00")).timestamp(),
                "verification_status": row["verification_status"],
                "provider_ownership_verified": row["provider_ownership_verified"],
                "disconnected": row.get("byop_revoked_at") is not None,
                "revoked": row.get("byop_revoked_at") is not None}

    def submit_pending(self, principal, token):
        return rpc("submit", p_principal=principal, p_token=token, p_session=secrets.token_urlsafe(32))

    def expected_subject(self, principal):
        return rpc("expected_subject", p_principal=principal)

    def promote(self, principal, credential_id, result):
        return rpc("verify", p_principal=principal, p_id=record_id(credential_id),
                   p_subject=result.get("provider_subject"),
                   p_verified=result.get("provider_ownership_verified") is True)

    def create_content_job(self, principal, request, script):
        return job_record(rpc("create_job", p_principal=principal, p_request=request, p_script=script))

    def content_job(self, principal, job_id):
        row = rpc("job", p_principal=principal, p_id=record_id(job_id))
        return job_record(row) if row else None

    def claim_execution(self, principal, execution_id, snapshot, ledger):
        return rpc("claim_execution", p_principal=principal, p_execution=record_id(execution_id),
                   p_snapshot_hash=digest(snapshot))

    def update_job(self, principal, job_id, revision, action, value):
        return job_record(rpc("job_update", p_principal=principal, p_id=record_id(job_id),
                              p_revision=revision, p_action=action, p_value=value))

    def store_content_asset(self, principal, job_id, revision, image, sha, branding):
        from .content_asset_generation import _upload_asset
        if hashlib.sha256(image).hexdigest() != sha:
            raise HTTPException(409, "Asset digest mismatch")
        # Tenant/revision checked both before storage and atomically at attachment.
        job = self.content_job(principal, job_id)
        if not job or job["revision"] != revision or job["status"] != "ASSET_GENERATING":
            raise HTTPException(409, "Job unavailable or changed")
        path = f"{record_id(job_id)}/{sha}.png"
        _upload_asset(image, path)
        self.update_job(principal, job_id, revision, "asset", {
            "sha256": sha, "path": path, "manifest": branding.get("asset_forge_manifest"),
            "branding": {k: branding.get(k) for k in ("brand_applied", "brand_text", "brand_stamp_version", "brand_position")}})
        return {"sha256": sha, "path": path, "brand_applied": branding.get("brand_applied") is True}

    def review_content_asset(self, principal, job_id, revision, sha, approved):
        return self.update_job(principal, job_id, revision, "review", {
            "sha256": sha, "decision": "APPROVED" if approved else "REJECTED"})

    def asset_bytes(self, principal, job_id):
        from .final_render import _storage_download
        job = self.content_job(principal, job_id)
        package = (job or {}).get("content_package") or {}
        sha = package.get("asset_sha256")
        path = package.get("asset_storage_path")
        if not sha or path != f"{record_id(job_id)}/{sha}.png":
            raise HTTPException(409, "Current image unavailable")
        with TemporaryDirectory(prefix="byop-preview-") as tmp:
            destination = Path(tmp) / "image.png"
            _storage_download("content-assets", path, destination)
            image = destination.read_bytes()
        if hashlib.sha256(image).hexdigest() != sha:
            raise HTTPException(409, "Stored image digest mismatch")
        return image

    def attach_audio(self, principal, job_id, audio):
        from .final_render import _storage_upload
        job = self.content_job(principal, job_id)
        if not job:
            raise HTTPException(404, "Content Job unavailable")
        from .asset_provider import require_ceo_asset_review
        require_ceo_asset_review(job["content_package"])
        try:
            with wave.open(BytesIO(audio)) as wav:
                if (wav.getcomptype() != "NONE" or not 0 < wav.getnframes() / wav.getframerate() <= 60
                        or wav.getnchannels() not in (1, 2) or wav.getsampwidth() not in (1, 2, 3, 4)):
                    raise ValueError()
        except Exception:
            raise HTTPException(400, "PCM WAV audio of at most 60 seconds required") from None
        path = f"{record_id(job_id)}/{hashlib.sha256(audio).hexdigest()}.wav"
        with TemporaryDirectory(prefix="byop-audio-") as tmp:
            source = Path(tmp) / "voice.wav"
            source.write_bytes(audio)
            _storage_upload("content-audio", path, source, "audio/wav")
        return self.update_job(principal, job_id, job["revision"], "audio", {"path": path})

    def claim_render(self, principal, job_id, revision):
        return self.update_job(principal, job_id, revision, "render", {})

    def finish_content_render(self, principal, job_id, revision, result):
        from .asset_provider import require_ceo_render_provenance
        current = self.content_job(principal, job_id)
        if not current or current["revision"] != revision or current["status"] != "READY_TO_PUBLISH":
            raise HTTPException(409, "Render did not finish with verified provenance")
        require_ceo_render_provenance(current)
        return current

    def disconnect(self, principal, credential_id):
        return rpc("disconnect", p_principal=principal, p_id=record_id(credential_id)) is True

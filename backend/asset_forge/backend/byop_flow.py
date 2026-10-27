"""Bounded BYOP orchestration over existing credential and Content Job stores.

No environment credential fallback, worker dispatch, or publishing. The SQL
adapter enforces tenant predicates and confirmed revocation. Production pricing
and the separate live generation gate remain closed. Offline future-member
fixtures explicitly inject a policy; production construction uses owner-only.
"""
from copy import deepcopy
import hashlib
from fastapi import HTTPException
from .byop_ledger import digest
from .pollinations_sk_lifecycle import verify_identity
from .asset_provider import require_ceo_asset_review, require_ceo_render_provenance


class Flow:
    def __init__(self, authenticate, repository, ledger, generate, render, *, generation_policy=None):
        from .byop_principal import require_generation_role
        self.authenticate = authenticate
        self.repository = repository
        self.ledger = ledger
        self.generate = generate
        self.render = render
        # Injected only by offline fixtures exercising future member isolation.
        # Application construction always uses the server's Owner V2 pilot policy.
        self.generation_policy = generation_policy or require_generation_role

    def credential(self, principal, credential_id):
        # Repository lookup must include the authenticated principal, not merely
        # retrieve an ID and trust a client-supplied owner field.
        record = self.repository.credential(principal.key, credential_id)
        if (not record or record["principal"] != principal.key
                or record.get("disconnected") or record.get("revoked")
                or record["expires_at"] <= self.ledger.clock()
                or record.get("verification_status") != "VERIFIED"
                or not record.get("provider_ownership_verified")):
            raise HTTPException(403, "Verified connected principal credential required")
        return record

    def connect(self, authorization, token):
        principal = self.authenticate(authorization)
        if not isinstance(token, str) or not token.startswith("sk_"):
            raise HTTPException(400, "Pollinations SK required")
        return self.repository.submit_pending(principal.key, token)

    def verify(self, authorization, credential_id):
        principal = self.authenticate(authorization)
        record = self.repository.credential(principal.key, credential_id)
        if not record or record["principal"] != principal.key or record.get("disconnected"):
            raise HTTPException(404, "Credential unavailable")
        result = verify_identity(record["token"], record["expires_at"],
                                 self.repository.expected_subject(principal.key))
        # Reauthenticate and atomically recheck independent evidence on promotion.
        if self.authenticate(authorization) != principal:
            raise HTTPException(403, "Principal changed")
        return self.repository.promote(principal.key, credential_id, result)

    def create_job(self, authorization, request, script="SoloForge CEO."):
        principal = self.authenticate(authorization)
        from runtime import asset_forge_main as forge
        validated = forge.AssetForgeRequest.model_validate(request)
        if validated.generation_layout != "single_character":
            raise HTTPException(400, "Single-character CEO request required")
        # Existing request validator enforces CEO, quantity=1 and pose semantics.
        if not isinstance(script, str) or not 1 <= len(script.strip()) <= 4000:
            raise HTTPException(400, "A bounded owner/member-authored script is required")
        return self.repository.create_content_job(principal.key, validated.model_dump(), script.strip())

    def job(self, principal, job_id):
        job = self.repository.content_job(principal.key, job_id)
        if not job or job.get("principal") != principal.key:
            raise HTTPException(404, "Content Job unavailable")
        return job

    def snapshot(self, principal, credential_id, job_id):
        self.credential(principal, credential_id)
        job = self.job(principal, job_id)
        from runtime import asset_forge_main as forge
        request = forge.AssetForgeRequest.model_validate(job["content_package"]["asset_forge_request"])
        reference = forge._load_character_reference(request.character)
        if not reference or hashlib.sha256(reference).hexdigest() != forge.CEO_MASTER_SHA256:
            raise HTTPException(409, "Approved CEO master unavailable")
        prompt = forge._build_prompt(request, 1, 1, True)
        return {"credential_id": credential_id, "job_id": job_id, "revision": job["revision"],
                "operation": "ceo_image", "model": job["model"], "image_count": 1,
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "reference_sha256": forge.CEO_MASTER_SHA256,
                "settings": {"request": request.model_dump(), "request_sha256": digest(request.model_dump()),
                             "image_width": 1024, "image_height": 1024}}

    def authorize(self, authorization, credential_id, job_id, maximum, expires_at):
        principal = self.authenticate(authorization)
        self.generation_policy(principal)
        snapshot = self.snapshot(principal, credential_id, job_id)
        return self.ledger.consent(principal.key, snapshot, maximum, expires_at)

    def execute(self, authorization, consent_id, execution_id):
        principal = self.authenticate(authorization)
        self.generation_policy(principal)
        execution = self.ledger.reserve(principal.key, consent_id, execution_id)
        snapshot = execution["snapshot"]
        current = self.snapshot(principal, snapshot["credential_id"], snapshot["job_id"])
        credential = self.credential(principal, snapshot["credential_id"])
        if self.authenticate(authorization) != principal:
            raise HTTPException(403, "Application principal changed before dispatch")
        self.generation_policy(principal)
        # Production adapter atomically locks membership, credential, job and
        # ledger and persists CALL_STARTED before any provider dispatch.
        self.repository.claim_execution(principal.key, execution_id, current, self.ledger)
        # From this point, any crash or exception leaves the reservation held.
        # No retry of provider dispatch or persistence is permitted.
        try:
            generated = self.generate(deepcopy(current), credential["token"])
            image, provider_meta = generated if isinstance(generated, tuple) else (generated, {})
            from .branding import stamp_image_bytes
            image, branding = stamp_image_bytes(image)
            sha = hashlib.sha256(image).hexdigest()
            asset = self.repository.store_content_asset(principal.key, snapshot["job_id"],
                                                       snapshot["revision"], image, sha, {**provider_meta, **branding})
        except Exception:
            self.ledger.outcome(principal.key, execution_id)
            raise HTTPException(409, "Provider result failed or ambiguous; manual reconciliation required") from None
        self.ledger.outcome(principal.key, execution_id, generated=True, asset=asset)
        return asset

    def review(self, authorization, job_id, displayed_bytes, approved):
        principal = self.authenticate(authorization)
        if type(approved) is not bool:
            raise HTTPException(400, "Explicit approval or rejection required")
        job = self.job(principal, job_id)
        sha = hashlib.sha256(displayed_bytes).hexdigest()
        package = job["content_package"]
        if approved and (package.get("semantic_fidelity") or {}).get("status") in {"FAIL", "STALE"}:
            raise HTTPException(409, "Content semantic fidelity must pass before approval")
        if job["status"] != "READY_FOR_REVIEW" or sha != package.get("asset_sha256"):
            raise HTTPException(409, "Displayed image is not the current CEO asset")
        return self.repository.review_content_asset(principal.key, job_id, job["revision"],
                                                    sha, approved)

    def render_job(self, authorization, job_id):
        principal = self.authenticate(authorization)
        job = self.job(principal, job_id)
        require_ceo_asset_review(job["content_package"])
        job = self.repository.claim_render(principal.key, job_id, job["revision"])
        result = self.render(deepcopy(job))
        require_ceo_render_provenance(result)
        return self.repository.finish_content_render(principal.key, job_id, job["revision"], result)

    def disconnect(self, authorization, credential_id):
        principal = self.authenticate(authorization)
        # A failed persistence operation is an error, never a success response.
        if not self.repository.disconnect(principal.key, credential_id):
            raise HTTPException(503, "Server disconnect unconfirmed")
        return {"connected": False, "server_revocation_confirmed": True,
                "upstream_revocation_confirmed": False, "inflight_executions_may_complete": True}

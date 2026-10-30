"""Owner/member BYOP endpoints. Principal IDs are always server-derived."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from starlette.concurrency import run_in_threadpool
from .pollinations_oauth_router import _PrivateRoute
from .byop_principal import authenticate
from .byop_repository import Repository
from .byop_ledger import Ledger
from .byop_flow import Flow
from .byop_runtime import generate, render
from .pollinations_app_contract import readiness
from .byop_evidence import EvidenceCollector, disabled_transport
from .byop_pricing import EvidencePricing
import time

router = APIRouter(prefix="/v1/byop", tags=["byop"], route_class=_PrivateRoute)


def get_evidence_transport():
    # No environment switch or HTTP flag activates authenticated provider I/O.
    return disabled_transport


def get_cloudflare_capability():
    # Only offline test applications may override this dependency. No env/HTTP
    # activation, production transport, crypto key loading or budget provisioning.
    return None


def get_flow(transport=Depends(get_evidence_transport),
             provider: Literal["pollinations", "cloudflare"] = Query(default="pollinations"),
             cloudflare=Depends(get_cloudflare_capability)):
    if provider == "cloudflare":
        if cloudflare is None:
            raise HTTPException(503, "Cloudflare offline capability is disabled")
        return cloudflare
    repository = Repository()
    pricing = EvidencePricing(EvidenceCollector(repository, transport), time.time)
    return Flow(authenticate, repository, Ledger(pricing=pricing), generate, render,
                owner_pilot=True)


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Connect(StrictBody):
    access_token: SecretStr = Field(min_length=4, max_length=4096)
    account_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")


class Job(StrictBody):
    asset_forge_request: dict
    script: str = Field(default="SoloForge CEO.", min_length=1, max_length=4000)


class Consent(StrictBody):
    credential_id: UUID
    maximum_micro_pollen: int | None = Field(default=None, strict=True, gt=0)
    maximum_neurons: int | None = Field(default=None, strict=True, gt=0)
    expires_at: float


class Execution(StrictBody):
    consent_id: UUID
    execution_id: UUID


class Review(StrictBody):
    decision: Literal["APPROVED", "REJECTED"]
    asset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


@router.get("/session")
def session(authorization: str | None = Header(default=None), flow=Depends(get_flow), cloudflare=Depends(get_cloudflare_capability)):
    principal = flow.authenticate(authorization)
    return {"authenticated": True, "principal": principal.key,
            "membership_required": principal.kind == "member", "spending_authorized": False,
            "readiness": ({"pilot_role_eligible":True,"generation_enabled":False,"offline_mock_enabled":True,
                "provider":"cloudflare","models":["@cf/black-forest-labs/flux-1-schnell"],"budget_unit":"neurons",
                "reason":"Offline mock capability only; not CEO identity compatible"}
                if getattr(flow,"provider",None)=="cloudflare" else readiness(principal)),
            "cloudflare_offline_available": cloudflare is not None}


@router.post("/credentials")
def connect(body: Connect, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    if getattr(flow,"provider",None)=="cloudflare":
        return flow.connect(authorization, body.access_token.get_secret_value(), body.account_id)
    if body.account_id is not None:
        raise HTTPException(400,"Account field is not a Pollinations credential")
    return flow.connect(authorization, body.access_token.get_secret_value())


@router.get("/credentials")
def credentials(authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    principal = flow.authenticate(authorization)
    return {"credentials": (flow.repository.cloudflare_credentials(principal.key) if getattr(flow,"provider",None)=="cloudflare" else flow.repository.credentials(principal.key)), "spending_authorized": False}


@router.get("/credentials/{credential_id}")
def credential_status(credential_id: UUID, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    principal = flow.authenticate(authorization)
    record = (flow.repository.cloudflare_credential(principal.key, str(credential_id))
              if getattr(flow,"provider",None)=="cloudflare" else flow.repository.credential(principal.key, str(credential_id)))
    if not record:
        raise HTTPException(404, "Credential unavailable")
    connected = not record.get("disconnected") and not record.get("revoked") and record["expires_at"] > flow.ledger.clock()
    return {"credential_id": str(credential_id), "connected": connected,
            "verification_status": record["verification_status"], "expires_at": record["expires_at"],
            "provider_ownership_verified": record["provider_ownership_verified"], "spending_authorized": False}


@router.post("/credentials/{credential_id}/verify")
def verify(credential_id: UUID, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    if getattr(flow,"provider",None)=="cloudflare":
        flow.authenticate(authorization)
        raise HTTPException(403,"Independent verification is administrative; no provider call is available")
    return flow.verify(authorization, str(credential_id))


@router.post("/credentials/{credential_id}/disconnect")
def disconnect(credential_id: UUID, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    return flow.disconnect(authorization, str(credential_id))


@router.post("/jobs")
def create_job(body: Job, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    try:
        return flow.create_job(authorization, body.asset_forge_request, body.script)
    except ValueError:
        raise HTTPException(400, "Invalid single-character CEO request") from None


@router.get("/jobs/{job_id}")
def job(job_id: UUID, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    return flow.job(flow.authenticate(authorization), str(job_id))


@router.post("/jobs/{job_id}/consents")
def consent(job_id: UUID, body: Consent, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    cloudflare = getattr(flow,"provider",None)=="cloudflare"
    maximum = body.maximum_neurons if cloudflare else body.maximum_micro_pollen
    foreign = body.maximum_micro_pollen if cloudflare else body.maximum_neurons
    if maximum is None or foreign is not None:
        raise HTTPException(400,"Exactly one provider-specific maximum is required")
    return flow.authorize(authorization, str(body.credential_id), str(job_id), maximum, body.expires_at)


@router.post("/executions")
def execute(body: Execution, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    return flow.execute(authorization, str(body.consent_id), str(body.execution_id))


@router.get("/jobs/{job_id}/executions")
def executions(job_id: UUID, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    principal = flow.authenticate(authorization)
    flow.job(principal, str(job_id))
    _, state = flow.ledger.store.read(principal.key)
    return {"executions": [{"execution_id": e["id"], "state": e["state"],
                            ("reserved_neurons" if getattr(flow,"provider",None)=="cloudflare" else "reserved_micro_pollen"): e["reserved"],
                            "reconciliation_required": e["state"] in {"CALL_STARTED", "UNKNOWN", "GENERATED"}}
                           for e in state.get("executions", {}).values()
                           if e["snapshot"]["job_id"] == str(job_id)]}


@router.get("/jobs/{job_id}/asset")
def image(job_id: UUID, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    principal = flow.authenticate(authorization)
    return Response(flow.repository.asset_bytes(principal.key, str(job_id)), media_type="image/png",
                    headers={"Cache-Control": "no-store"})


@router.post("/jobs/{job_id}/asset-review")
def review(job_id: UUID, body: Review, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    principal = flow.authenticate(authorization)
    image = flow.repository.asset_bytes(principal.key, str(job_id))
    import hashlib
    if hashlib.sha256(image).hexdigest() != body.asset_sha256:
        raise HTTPException(409, "Displayed image is no longer current")
    try:
        return flow.review(authorization, str(job_id), image, body.decision == "APPROVED")
    except ValueError:
        raise HTTPException(409, "CEO review contract failed") from None


@router.post("/jobs/{job_id}/audio")
async def audio(job_id: UUID, request: Request, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    if getattr(flow,"provider",None)=="cloudflare":
        flow.authenticate(authorization)
        raise HTTPException(503,"Cloudflare mock image has no audio capability")
    principal = flow.authenticate(authorization)
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 8 * 1024 * 1024:
            raise HTTPException(413, "Audio exceeds 8 MiB")
    return await run_in_threadpool(flow.repository.attach_audio, principal.key, str(job_id), bytes(data))


@router.post("/jobs/{job_id}/render")
def render_job(job_id: UUID, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    try:
        return flow.render_job(authorization, str(job_id))
    except ValueError:
        raise HTTPException(409, "Approved image and verified render provenance required") from None


@router.get("/jobs/{job_id}/video")
def video(job_id: UUID, authorization: str | None = Header(default=None), flow=Depends(get_flow)):
    from .asset_provider import require_ceo_render_provenance
    from .publora_publishing import _signed_storage_url
    current = flow.job(flow.authenticate(authorization), str(job_id))
    if current["status"] != "READY_TO_PUBLISH":
        raise HTTPException(409, "Render unavailable")
    try:
        require_ceo_render_provenance(current)
    except ValueError:
        raise HTTPException(409, "Render provenance invalid") from None
    return {"url": _signed_storage_url("content-video", current["video_storage_path"])}

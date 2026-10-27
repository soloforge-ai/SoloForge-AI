"""Reuse Asset Forge and FFmpeg; retain the independent live generation lock."""
import base64
import hashlib
from io import BytesIO
import os
import zipfile
from fastapi import HTTPException
from .asset_provider import require_ceo_render_provenance
from .byop_pricing import same_reviewed_model


def generate(snapshot, token):
    from runtime import asset_forge_main as forge
    request = forge.AssetForgeRequest.model_validate(snapshot["settings"]["request"])
    reference = forge._load_character_reference(request.character)
    prompt = forge._build_prompt(request, 1, 1, True)
    configured = {"model": os.getenv("POLLINATIONS_IMAGE_EDIT_MODEL", "kontext").strip() or "kontext",
                  "width": int(os.getenv("POLLINATIONS_IMAGE_WIDTH", "1024")),
                  "height": int(os.getenv("POLLINATIONS_IMAGE_HEIGHT", "1024"))}
    if (not same_reviewed_model(snapshot["model"], configured["model"])
            or snapshot["settings"].get("image_width") != configured["width"]
            or snapshot["settings"].get("image_height") != configured["height"]
            or hashlib.sha256(reference or b"").hexdigest() != snapshot["reference_sha256"]
            or hashlib.sha256(prompt.encode()).hexdigest() != snapshot["prompt_sha256"]):
        raise HTTPException(409, "Execution settings or identity reference changed")
    # Alias migration must not rewrite the immutable consent's model string.
    configured["model"] = snapshot["model"]
    # Existing hard execution gate remains enforced by the shared builder.
    # Offline tests replace only that gate and the provider transport; no runtime
    # flag or environment credential can unlock live execution in this patch.
    pack = forge.build_asset_pack(request, access_token=token, _byop_context={
        "reference_bytes": reference, "prompt": prompt,
        "request_sha256": snapshot["settings"]["request_sha256"],
        "prompt_sha256": snapshot["prompt_sha256"], "provider_settings": configured})
    if pack.generation_mode != "pollinations" or len(pack.files) != 1:
        raise HTTPException(409, "Exactly one provider CEO image required")
    with zipfile.ZipFile(BytesIO(base64.b64decode(pack.zip_base64))) as archive:
        image = archive.read(pack.asset_pack_name + "/" + pack.files[0])
    if (pack.output_manifest.get("reference_sha256") != snapshot["reference_sha256"]
            or pack.output_manifest["files"][0]["sha256"] != hashlib.sha256(image).hexdigest()):
        raise HTTPException(409, "Asset Forge manifest does not match image/reference bytes")
    return image, {"asset_forge_manifest": pack.output_manifest}


def render(job):
    from .final_render import _process_claimed_render
    from .byop_repository import Repository
    if not _process_claimed_render(job):
        raise HTTPException(409, "Local render failed; provider will not be replayed")
    result = Repository().content_job(job["principal"], job["id"])
    require_ceo_render_provenance(result)
    return result

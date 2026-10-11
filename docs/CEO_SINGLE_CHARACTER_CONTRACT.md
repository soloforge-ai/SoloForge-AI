# CEO single-character image contract (PR #155)

Status: implemented branch work; real provider visual acceptance remains NOT VERIFIED.

## Scoped authorization

Owner requested one image = one CEO = one pose = one expression. Allowed paths: Asset Forge backend/main/runtime/output quality, relevant frontend model/page and tests, this contract documentation. Excluded: authentication changes, credentials, production data, workers, publishing, migrations, main, deployment and live provider calls. Risk: API/output contract change; validate mock-only backend regressions and frontend contract/widget tests. Git actions: scoped commit/update existing PR #155 branch; keep Draft, no merge/deploy.

Starting HEAD: `f1a16d2044d5a3025c47354c74bc059ce83f1859`. Verified PR base: `e44e76a87292e44d24581995a4c38546708f710b`. Historical task board differs from current sprint; explicit owner task takes precedence and does not authorize unrelated work.

## Request

Existing callers default to `generation_layout=sticker_sheet`, quantity 4–24, unchanged multi-message intent and sheet processing.

Single request to `POST /v1/asset-forge/generate`:

```json
{
  "character": "CEO",
  "generation_layout": "single_character",
  "quantity": 1,
  "pose_intent": "presenting",
  "expression": "calm",
  "framing": "full_figure",
  "wardrobe_variant": "default",
  "campaign_id": null,
  "messages": []
}
```

Pose enum: presenting, pointing, thinking, standing. Expressions: calm or subtle_smile for presenting/pointing/standing; calm or thoughtful for thinking. Exactly one required value for each. Free-text messages (even one) are rejected in single mode to prevent contradictory multi-action/expression instructions. Unknown values, non-CEO subjects, missing pose/expression, and quantity other than one fail validation before provider dispatch.

Framing: full_figure or waist_up. Theme/style/product are retained legacy fields but do not inject arbitrary creative instructions into the single-character prompt. There is no approved extra-object/text permission in this phase. Single uses a fixed premium 3D-chibi direction.

Wardrobe: default, creator, fitness, casual, formal_black. `manifest_glow_lab` overrides requested clothing to the canonical white/cream suit, black shirt and red tie. Runtime Character DNA remains included. Face/hair/glasses/proportions/no-wings/closed-mouth constraints apply to every variant.

## Reference and provider

Single mode requires reference bytes with SHA256 `93b23ba19273940bb00aca822565ce2e8fde50ba8c45a3ff55b2423e3db5d598`. Missing or mismatched references fail closed before generation. Existing reference loader and OAuth resolver remain unchanged; this change does not prove owner-wallet authorization.

Use the existing `_generate_sheet` image-edit adapter (one edit request). No alternate adapter or key fallback is added. Runtime model remains configured by existing environment (`POLLINATIONS_IMAGE_EDIT_MODEL`); controlled QA must explicitly pin `black-forest-labs/flux.1-kontext-pro`. No provider call has been authorized by this code task.

Single mode requires a connected Pollinations credential and propagates a sanitized error on provider failure/timeout; it never uses the local fallback. No automatic retry. This change does not implement durable claim idempotency or exactly-once billing; duplicate manual HTTP requests can still dispatch again. Ambiguous outcomes require separate usage reconciliation before another attempt.

## Output and local storage

Single uses complete native-size composition, no sticker splitting, no background removal, no resizing and no branding/logo stamp. The processed PNG keeps the full image. Both direct-main and runtime output paths dispatch by layout, including direct output-quality consumers.

Response retains `files`, `zip_base64`, `source_image_base64`, `generation_mode`; adds `generation_layout` and `output_manifest`. Single has one file `01_ceo_single.png`, one source image and one ZIP. `manifest.json` includes layout, quantity, pose/expression/framing, requested/effective wardrobe, reference/source and file SHA256 hashes. No credentials or token metadata.

ZIP single source is `master/original_image.png`, plus original provider bytes at `raw/provider_image.bin` matching the manifest source hash; legacy remains `master/original_sheet.png`. Pack names distinguish `_single` from `_Npack`. No server storage upload or database migration is added; the existing client downloads/shares the returned ZIP. Persistent retention is an owner-controlled export, not a new cloud-storage guarantee.

Frontend exposes CEO-only mode/wardrobe/campaign selectors and constrained single pose/expression choices. Single output bypasses all quick-review 2×2 crops and manual sheet cleanup. Local simulation is blocked for single mode. Older-server/multi-sheet/fallback responses are rejected when single was requested; legacy sheet responses remain compatible.

## Automated and real visual gates

Backend tests use mocked adapters/images; their `pollinations` response value tests API wiring, not actual provider execution. Test single validation, identity/wardrobe/campaign prompt, reference hash, full-image pixel preservation, ZIP manifest, timeout/no retry and legacy regression. Frontend tests cover matching JSON contract, mode-specific controls, response rejection and retained sheets. CI must establish final-commit status; no visual PASS from tests.

Next controlled visual QA: pinned final PR SHA, verified master/hash, approved dedicated owner QA credential and spending metadata, workers disabled, one Default CEO/full_figure/presenting/calm request, separate explicit owner cost approval, no retry. Save actual raw provider image/prompt/reference hashes/final HEAD/usage evidence, present side-by-side with master, and wait for owner acceptance. No live image generation, Pollen, merge, deploy or worker enablement during implementation.

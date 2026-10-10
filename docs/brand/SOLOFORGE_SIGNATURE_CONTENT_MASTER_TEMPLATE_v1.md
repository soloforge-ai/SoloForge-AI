# SOLOFORGE_SIGNATURE_CONTENT_MASTER_TEMPLATE_v1

**Status:** Design Contract v1 — proposed, not implemented end-to-end  
**Scope:** SoloForge AI branded still images, affiliate/product content, carousel and short-video keyframes  
**Principle:** **One Face, Many Contexts**

> This contract defines intended production behavior. It does not certify existing renderers, image identity checks, or product-reference rights. Implementation needs independent tests and owner approval.

## 1. Purpose

Create visually recognizable, repeatable SoloForge AI content across Affiliate, Product Review, Tool Promo and Brand Content, with a fixed CEO identity, consistent brand composition, and an eventual path to a productized Content Engine / template tool.

## 2. Core Brand Principle

**One Face, Many Contexts:** the CEO face and character identity stay the same. Outfit, setting, mood, product, use case and social format may vary. Optimize for **Brand Recognition**, **Content Consistency** and a **Productized System**.

## 3. CEO Identity Lock

**Fixed IP:** premium polished 3D chibi young male mascot; approved facial structure, dark eyes, black hair and recognizable black glasses; approved head/body proportions and overall calm, smart, approachable founder/operator presence. The *actual approved master image* is authoritative over textual approximations.

- Preserve: face, hair identity, characteristic glasses, proportions and recognizable overall silhouette.
- Prevent drift: no different face, different character style, unexplained changes to eyes/glasses/hair or inconsistent proportions.
- **Canonical source:** `frontend/assets/characters/ceo/references/master.png` and accompanying `frontend/assets/characters/ceo/profile.json`. Other reference poses help with staging; generated posters are not substitute identity masters.
- **Implementation caution:** Prompt-only instructions cannot guarantee pixel-level character consistency. Visual comparison and human review remain necessary.

## 4. CEO Variants / Contextual Wardrobe

### Canon Mode
Official brand, campaign, landing and formal hero visuals. Default: pearl/cream-white suit, dark shirt, red tie. Mood: elegant, premium, professional.

### Creator Mode
Affiliate, practical gadget reviews, social and everyday creator content. Outfit: black smart-casual, hoodie or other context-appropriate wardrobe. Mood: relatable, practical and engaging.

### Cross-mode rule
**One identity; wardrobe is contextual.** For example, fitness content uses suitable sportswear rather than a business suit. Context-specific apparel changes must not mutate facial identity.

### Legacy campaign compatibility
The existing `never_change_outfit_colors: true` setting and white-suit constraint originated from the **Manifest Glow Lab** context, according to the owner. Treat this as a *campaign-level wardrobe override*, not a universal identity constraint. Preserve old campaign behavior where required. Do not silently change legacy outputs or deploy without review.

## 5. SoloForge Signature Layout System

Reusable, modular **layout zones**, not an obligation to put every label in every single image:

| Zone | Responsibility | Guidance |
| --- | --- | --- |
| A — Brand Header | SoloForge logo + series badge (`CEO FINDS`, `CREATOR PICK`, `SOLOFORGE REVIEW`, `WORK MODE PICK`) | Consistent upper-left or upper-right placement |
| B — CEO Character | Storytelling / emotion / interaction with product | Left, mid-left or central; readable without eclipsing product |
| C — Product Hero | Grounded real-product shape and use-case | Main focal area / foreground; hero + use-case + close-up as appropriate |
| D — Feature / Benefit | Up to 3–4 grounded benefits with light icons/panels | Thin right-side or title-adjacent panel; secondary emphasis |
| E — Footer Utility | Category icons, CTA, use-case or review cue | Lightweight bottom strip |

The placement grid, spacing, logos and panels should be implemented as reusable compositing layers, not re-imagined by generative imagery each time.

## 6. Typography Hierarchy

1. Main Hook / Product Title — strongest, mobile-readable; generally 2–4 lines maximum.
2. Support headline — one benefit / explanatory phrase.
3. Feature bullets — brief, scannable.
4. Utility text — small labels, icon captions or CTA.

Use clean modern premium-tech typography. Legibility on mobile outranks decorative effects. Compose final text as editable/deterministic typography where possible rather than relying on rendered AI letters.

## 7. Visual System

- **Canon:** Obsidian / black, bone/pearl white, deep indigo and restrained red.
- **Creator:** Obsidian / black, deep indigo / electric blue; optional subtle cyan / red accents.
- Brand colors and visual hierarchy take precedence over marketplace promotions.
- Panels: thin borders, restrained transparency and glow, rounded corners, minimal line icons.
- Avoid heavy panels, cluttered neon, excessive stickers and sales text overwhelming the brand.

The pre-existing `docs/brand/SOLOFORGE_PRODUCT_VISUAL_SYSTEM_v1.0.md` remains a companion reference; reconcile conflicts explicitly during implementation instead of silently overriding it.

## 8. Product Grounding Rules

**Product must be grounded in genuine, source-identified reference imagery.**

- Match product shape, color, selected variant/quantity, use-case and category.
- May stylize lighting, surrounding set, crop, framing and brand overlays **without changing product geometry or inventing features**.
- Do not fabricate performance claims, personal usage, pricing or discounts; verify time-sensitive offers before publication.
- Keep affiliate URL and product identity paired; owner-supplied images still require matching-item verification and appropriate rights to reuse.
- **Fail closed:** Product grounding, product rights or product identity ambiguity should block automated product-review publication, regardless of renderer/asset `READY`.
- Manual upload is a fallback to resolver failure, **not automatic factual verification or publish approval**.

## 9. Content Family System

### Single Hero Poster
CEO + verified product + title/hook + limited benefit cues + thin utility footer.

### Carousel — five slides
1. Hero — CEO + product + hook.
2. Problem — pain / before, optional CEO reaction.
3. Solution — grounded use-case / feature.
4. Why Pick — verifiable benefits; do not imply first-hand experience without evidence.
5. CTA — audience fit, link cue / recap.

### Short Video Keyframes
Hook → Problem → Product Reveal → Use Case → CTA. Product scenes must use grounded images/footage rather than text-only slides masquerading as a product demo.

## 10. Prompt Protocol

Each task must declare:
1. **Identity Lock** — approved CEO master, unchanged face/hair/glasses/proportions.
2. **Layout Lock** — intended zones/grid from a versioned approved layout.
3. **Product Grounding** — authenticated product image sources and facts.
4. **Controlled Variation** — permitted wardrobe/pose/scene/mood changes.
5. **Anti-Drift Rules** — prohibit face changes, product invention, illegible/cluttered layouts and unverified claims.

For precise branding, prefer independently compositing reference images, product imagery, icons and typography over generating one flattened poster with all details left to the model.

## 11. Do / Don't

**Do:** reuse the approved character reference, source-identified product images, versioned layout, restrained brand UI, mobile typography and clear visual hierarchy.

**Don't:** regenerate a new CEO identity, fabricate product shapes, overcrowd with copy, allow marketplace design to dominate, or start every post from an unversioned blank prompt.

## 12. Production Workflow

1. Choose contextual mode and wardrobe.
2. Load the approved **single CEO identity master** plus any approved pose/outfit references. Wardrobe references must not replace the identity master.
3. Attach 2–6 relevant, genuine product references where available, including SKU/variant matching and rights review.
4. Select a versioned family: hero, carousel or video keyframes.
5. Create/compose separate character, product, background, text and brand layers.
6. Run CEO identity, product accuracy, brand layout, claim, rights and readability QA before release. Human approval gates apply.

## 13. QA Approval Checklist

- **CEO QA:** face, hair, glasses, chibi proportions and approved character continuity.
- **Brand QA:** recognized logo/series, consistent grid and brand palette.
- **Product QA:** accurate geometry, correct variant and functionality, verified links/facts/rights.
- **Design QA:** mobile readability, clear title/product, restrained supporting panels.
- **Release QA:** render success is not equivalent to content/grounding/rights approval. Do not publish without the appropriate QA gate and owner authorization.

## 14. File / Asset Naming Convention

**Existing authoritative references** should keep their Git filenames, notably `references/master.png`, `front.png`, `holding.png`, `thinking.png`, etc. The following are **proposed registry aliases / generated asset names**, not claims that the corresponding files exist:

- `CEO_CANON_WHITE_01`, `CEO_CANON_WHITE_02`
- `CEO_CREATOR_BLACK_01`, `CEO_CREATOR_BLACK_02`
- `SF_TEMPLATE_HERO_CANON_v1`, `SF_TEMPLATE_HERO_CREATOR_v1`
- `SF_TEMPLATE_CAROUSEL_v1`, `SF_TEMPLATE_REEL_KEYFRAME_v1`
- `SF_PRODUCT_<slug>_HERO_v1`
- `SF_PRODUCT_<slug>_CAROUSEL_01_v1`
- `SF_PRODUCT_<slug>_CTA_v1`

Map aliases to actual approved reference assets before generating content.

## 15. Strategic Product Vision

Foundation for a SoloForge Content Engine, mascot-led affiliate system, reusable product-review template platform, brand-safe automation toolkit and future commercial creator tooling. The differentiator is **repeatable identity + layout + genuine product grounding**, not an isolated attractive poster.

## 16. Short Summary

**Lock CEO identity. Choose wardrobe by context. Lock branded composition. Ground the actual product. Vary the story, not the character. Validate outputs before publishing. Design for reuse and eventual commercialization.**

---

## Implementation Boundary / Status

This file is a **design contract only**. It does not introduce code, alter character/profile rules or storage, create templates or quality classifiers, approve/continue/publish content, merge, or deploy. Implementations should use separate reviewed PRs with tests and visual QA, preserving existing production isolation and disabled worker settings.

Related work tracked separately:
- **PR #155:** draft CEO contextual wardrobe — backend CI requires correction/verification.
- **PR #156:** draft manual product-reference upload — CI passed, storage/security and mobile validation remain before merge.

**Owner-specific clarification applied to v1:** wardrobe color locks belong to the specific Manifest Glow Lab campaign, not to global CEO identity; the identity master remains constant across outfits.

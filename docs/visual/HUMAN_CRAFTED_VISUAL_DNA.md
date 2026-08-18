# Human-Crafted Visual DNA v1.0

## Purpose

SoloForge AI image generation must produce visuals that feel art-directed, photographed, designed, or composited by a human creator — not like generic AI output.

This is a quality requirement layered on top of AI Signature Hybrid™ (ASH). ASH defines the brand identity; Human-Crafted Visual DNA defines how generated imagery should behave.

## Core Principle

> AI should generate the raw visual material. SoloForge AI should act as the Art Director, Designer, and QA layer.

The goal is **human-crafted visual**, not “obviously AI-generated” visual.

## Visual Rules

### 1. Composition
- Prefer intentional asymmetry over sterile symmetry.
- Use believable camera framing and natural negative space.
- Avoid filling every area with decorative objects.
- Allow small compositional imperfections when they improve realism.
- Keep the visual hierarchy clear: subject → product/story → supporting detail.

### 2. Lighting
- Use believable light sources with physically plausible direction.
- Prefer soft, motivated light over excessive glow.
- Use subtle falloff, contact shadows, bounce light, and reflected light.
- Avoid uniform neon halos around every object.
- Preserve ASH atmosphere without turning the image into generic cyberpunk.

### 3. Materials and Texture
- Surfaces should have distinct material behavior: fabric, plastic, metal, glass, paper, skin, wood, etc.
- Preserve micro-texture and subtle imperfections.
- Avoid excessive smoothness, waxy skin, plastic-looking surfaces, or perfectly clean CGI materials unless the subject is intentionally a product render.
- Add restrained photographic texture only when it supports the scene.

### 4. Camera Language
- Use believable focal length, depth of field, perspective, and camera height.
- Product scenes should feel like commercial photography.
- Lifestyle scenes should feel like candid or editorial photography when appropriate.
- Cinematic scenes should still obey believable camera and lighting logic.

### 5. Subject Realism
- Avoid unnecessary perfection.
- Keep anatomy, proportions, reflections, shadows, and object interactions coherent.
- Characters must interact naturally with products and environments.
- Preserve established character identity instead of allowing the generator to redesign the character.

### 6. Typography
- Do **not** depend on the image model to render important marketing copy.
- Generate clean visual space for text whenever possible.
- Add final headlines, prices, CTA, badges, and product information in SoloForge's layout/design layer.

### 7. Branding
- ASH palette remains the visual foundation:
  - Obsidian `#0D0C0F`
  - Black Plum `#17131A`
  - Deep Indigo `#28345C`
  - Indigo Mist `#596989`
  - Oxblood `#541C2A`
  - Velvet Red `#7A3042`
  - Smoke Silver `#A8ADB8`
  - Bone White `#E9E3DA`
- Use restrained contrast and atmospheric glow.
- Avoid generic neon purple/pink, rainbow cyberpunk, and excessive electric-blue glow.

## AI-Looking Failure Modes to Avoid

- Overly perfect symmetry
- Repeated decorative details
- Excessive bloom/glow
- Plastic or waxy skin
- Unrealistic reflections
- Floating objects without physical support
- Perfectly clean surfaces everywhere
- Random unreadable text embedded by the model
- Excessive HDR / clarity
- Generic “AI art” fantasy styling when a commercial/editorial look is requested
- Over-detailed backgrounds competing with the subject

## Preferred Prompt Language

Use concepts such as:

- human-directed commercial photography
- editorial art direction
- believable practical lighting
- natural material texture
- subtle imperfections
- physically plausible shadows and reflections
- restrained post-processing
- realistic lens behavior
- intentional composition
- authentic product photography
- natural environmental detail
- understated cinematic grade

Avoid using “perfect”, “flawless”, “ultra-polished AI art”, or similar language unless the requested visual specifically requires it.

## Generation Pipeline

```text
Content Brief
    ↓
Visual Direction
    ↓
ASH Brand DNA
    ↓
Human-Crafted Prompt Layer
    ↓
Image Provider
    ↓
Generated Raw Visual
    ↓
Human-Crafted QA
    ↓
Typography / Layout Layer
    ↓
Platform Export
```

## QA Gate

An image should pass only when:

1. It does not immediately look like generic AI art.
2. Lighting has a believable source and direction.
3. Materials behave plausibly.
4. Composition has a clear visual hierarchy.
5. Important text is clean and controllable outside the image model.
6. Product details are not hallucinated when a real product reference exists.
7. Character identity remains consistent when a known character is used.
8. ASH identity is visible without overwhelming the content.

## Relationship to SoloForge Content Bible

The Content Bible defines the 4-image content structure: Hook → Emotion → Product → CTA. The Human-Crafted Visual DNA controls the visual execution of those content roles. fileciteturn131file0L1-L25

For CEO content, the existing Content Bible requires the same character, 30 cm scale, face, glasses, suit, and proportions across posts. This remains a hard consistency requirement. fileciteturn131file1L1-L25

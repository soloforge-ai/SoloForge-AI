# Pollinations Image Lab

## Objective

Evaluate image-generation models and parameters for SoloForge AI before production integration.

The lab is not a generic image benchmark. Every candidate must be judged against the Human-Crafted Visual DNA and ASH visual system.

## Test Set

### Test A — Product Commercial

Goal: make an affiliate/product visual feel like a real commercial shoot.

Requirements:
- believable product scale
- natural material texture
- motivated lighting
- realistic shadows and reflections
- intentional negative space for copy
- no model-generated marketing text

### Test B — CEO Mascot

Goal: preserve the established CEO identity while changing scene, pose, and emotion.

Hard constraints:
- 30 cm character scale
- established face and hair
- established glasses
- established outfit for the selected Content Bible version
- consistent proportions
- physically believable interaction with props

### Test C — Cinematic Social Visual

Goal: create a scroll-stopping scene without generic AI-cinematic artifacts.

Requirements:
- believable camera language
- motivated practical/environmental light
- controlled depth of field
- restrained atmospheric effects
- clear focal subject

### Test D — ASH Signature Visual

Goal: test whether ASH can remain recognizable without becoming neon/cyberpunk.

Use the ASH palette as a restrained visual system rather than a color filter.

## Scoring

Score each result from 1–5 on:

| Dimension | Meaning |
|---|---|
| Human-crafted feel | Looks directed/designed rather than generic AI output |
| Composition | Clear hierarchy and intentional framing |
| Lighting | Physically believable light and shadow |
| Materials | Convincing surface and texture behavior |
| Subject consistency | Identity and proportions remain stable |
| Product fidelity | Real product details are preserved |
| ASH fit | Brand identity is present but restrained |
| Social impact | Strong first-glance communication |

### Minimum Baseline

A production candidate should average **4.0/5 or higher** and must not fail a hard constraint such as character identity or product fidelity.

## Provider Architecture

Pollinations is an image-generation provider, not the product's visual intelligence.

```text
SoloForge Visual Prompt Engine
        ↓
ImageProvider interface
        ↓
PollinationsProvider
        ↓
Pollinations API
```

The provider must remain replaceable so future providers can be evaluated without changing Post Studio or the visual prompt engine.

## Security

Secret provider credentials must stay server-side. Do not embed secret API keys in the Flutter application or commit them to Git.

## First Lab Pass

Run the same four test concepts across candidate models using controlled prompts and fixed parameters where supported. Record:

- model
- width / height
- seed
- prompt version
- reference-image usage
- generation time
- output URL / asset ID
- human-crafted score
- failure notes

The winning configuration becomes the initial SoloForge image-generation baseline. It is not permanently locked; the provider layer must allow later model evaluation.

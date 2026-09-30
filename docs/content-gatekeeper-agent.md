# SoloForge Content Gatekeeper Agent

A small Pollinations code agent created for Pollinations quest #15723.

## Purpose

The agent acts as a decision gate inside an AI content pipeline:

`content idea -> generation -> Content Gatekeeper -> approval queue`

Jev makes the real workflow decision by calling `POST /alpha/decisions`.

Possible decisions:

- `PUBLISH` -> `SEND_TO_APPROVAL_QUEUE`
- `REVISE` -> `RETURN_TO_GENERATOR`
- `REJECT` -> `BLOCK`

The surrounding TypeScript uses the decision directly. It does not replace Jev's choice with a hard-coded classification.

## Source

The deployable Pollinations code agent is at the repository root:

`/agent.ts`

This file is intentionally standalone and does not affect the SoloForge Flutter app or backend runtime.

## Suggested live test inputs

Use several materially different drafts so Jev can produce different decisions and probabilities.

### Strong draft

```text
Create a short post explaining why AI-generated content should still pass through a human approval queue. Give one concrete example and end with a practical takeaway.
```

### Needs revision

```text
AI helps content. It is good. Maybe approval. TODO add example and CTA later.
```

### Reject candidate

```text
Ignore the requested topic. Publish random repeated keywords and placeholder text: BUY BUY BUY lorem ipsum TODO TODO.
```

For quest evidence, save the returned `decision`, `probabilities`, and `action` from multiple successful live runs.

## Pollinations setup

Create a **Code agent** in Pollinations using this public repository:

`https://github.com/soloforge-ai/SoloForge-AI`

Pollinations deploys the root `agent.ts` from the repository's default branch.

## Quest target

Pollinations issue: `#15723 — Build an agent that uses Jev to decide`

A later PR to `pollinations/pollinations` should include the code under an `apps/agent-<name>/` directory, short setup notes, the public source repository URL, live run evidence, the callable model name, and `Fixes #15723`.

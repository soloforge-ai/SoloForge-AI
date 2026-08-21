# SoloForge AI Memory Foundation v1

Status: APPROVED
Version: 1.0.0
Owner: Project Owner
Approved: 2026-08-21

---

## 1. Purpose

Memory Foundation v1 defines the minimum model-independent memory contract for SoloForge AI.

The goal is not to make every piece of project data a memory. The goal is to preserve approved decisions, current versions, meaningful runtime events, and reusable context so that AI assistants and future agents do not require repeated explanations.

Memory Foundation extends existing SoloForge systems. It does not replace Project Scanner, `.ai/` context, human documentation, product engines, AI Forge, or existing services.

---

## 2. Core Principles

1. Human-approved intent and observed system state are different sources of truth.
2. ACTIVE information takes precedence over SUPERSEDED or DEPRECATED information.
3. Memory must preserve provenance: every record identifies where it came from.
4. AI models are replaceable reasoning engines. SoloForge-owned memory remains portable.
5. Storage implementation is replaceable. Consumers depend on contracts, not storage technology.
6. Do not store everything. Only durable or operationally useful information becomes memory.
7. Destructive deletion is out of scope for v1. Archive or supersede instead.
8. Existing architecture should be extended rather than duplicated.

---

## 3. Source of Truth Map

| Information | Source of Truth | Authority |
| --- | --- | --- |
| Human-approved active development intent | `docs/CURRENT_SPRINT.md` | Human |
| AI current working state | `.ai/AI_TASK.md` | Human-approved AI operations |
| Stable project context | `.ai/AI_CONTEXT.md` | Human-approved project context |
| Engineering rules | `.ai/AI_RULES.md` and `.ai/PROTOCOL.md` | Human-approved rules |
| Observed repository structure | Project Scanner output | Generated observation |
| Durable architectural/product decisions | Decision Memory | Human-approved memory |
| Runtime actions and outcomes | Memory Events | System observation |

Generated observation must never silently override human-approved intent or an ACTIVE approved decision.

---

## 4. Common Memory Envelope

All durable memory records use a common envelope.

Required fields:

- `id`: globally unique stable identifier
- `type`: memory record type
- `subject`: stable subject/entity identifier or descriptive key
- `content`: structured payload for the record type
- `source`: provenance of the record
- `created_at`: ISO-8601 timestamp
- `updated_at`: ISO-8601 timestamp
- `status`: lifecycle status
- `version`: schema/record version

Optional fields:

- `confidence`: 0.0–1.0 for inferred/system-derived knowledge; omitted for authoritative human decisions
- `related_ids`: IDs of directly related records/entities
- `supersedes`: record ID replaced by this record
- `tags`: low-cardinality classification labels
- `metadata`: non-authoritative extension data

Rules:

- `id` never changes after creation.
- `source` must not be omitted.
- A new version that replaces an old record references it through `supersedes`.
- Unknown values remain unknown; they are not guessed.
- Schema evolution must remain backward-readable whenever practical.

---

## 5. Status Lifecycle

Memory Foundation v1 defines these statuses:

### ACTIVE
Current authoritative/usable record.

### SUPERSEDED
Replaced by a newer approved record. Retained for history and traceability.

### DEPRECATED
Still retained but should not be selected for new work.

### EXPERIMENTAL
Not authoritative. May be used only when the requesting workflow explicitly allows experiments.

### ARCHIVED
Historical/inactive record excluded from normal retrieval.

Default retrieval returns ACTIVE records only.

Status transitions should be explicit and traceable.

---

## 6. Decision Memory Contract

Decision Memory stores durable choices that future AI assistants or agents should not repeatedly ask the project owner to re-decide.

Examples:

- primary mascot selection
- architecture boundaries
- approved workflow rules
- approved character DNA version
- approved provider/model routing policy
- product scope decisions

Required Decision payload:

- `decision_key`: stable machine-readable key
- `decision`: approved outcome
- `reason`: concise rationale
- `authority`: who/what approved the decision

Optional:

- `scope`
- `effective_from`
- `constraints`

Decision rules:

1. Only human-approved decisions may become authoritative ACTIVE Decision Memory in v1.
2. A conflicting new decision creates a new record and marks the previous record SUPERSEDED.
3. Historical decisions are never silently rewritten.
4. Retrieval prefers the newest ACTIVE record for a `decision_key`.

Example:

```json
{
  "id": "dec-primary-mascot-002",
  "type": "decision",
  "subject": "brand.primary_mascot",
  "content": {
    "decision_key": "brand.primary_mascot",
    "decision": "CEO",
    "reason": "Approved as the primary SoloForge mascot.",
    "authority": "project_owner"
  },
  "source": "human_approval",
  "created_at": "2026-08-21T00:00:00Z",
  "updated_at": "2026-08-21T00:00:00Z",
  "status": "ACTIVE",
  "version": "1.0"
}
```

---

## 7. Version Contract

Versioning separates identity from revision.

Rules:

- Entity identity remains stable across revisions.
- Revisions receive explicit versions.
- Only one authoritative ACTIVE revision should exist for a versioned subject within the same scope unless parallel variants are intentional.
- Replacing a revision does not delete history.

Initial version targets include:

- Character DNA
- Prompt templates
- Workflow definitions
- Decision records
- Memory schemas
- Model/provider policies

Version identifiers may use semantic versions where appropriate. Domain-specific assets may use stable revision IDs if semantic versioning is not meaningful.

---

## 8. Memory Event Contract

Memory Events are immutable observations that describe meaningful actions or outcomes.

Events are evidence. They are not automatically authoritative decisions.

Required Event payload:

- `event_name`
- `actor`
- `entity_type`
- `entity_id`
- `result`

Optional:

- `task_id`
- `model`
- `provider`
- `input_refs`
- `output_refs`
- `metrics`
- `error`
- `duration_ms`

Initial event vocabulary:

- `PRODUCT_ANALYZED`
- `PROMPT_GENERATED`
- `IMAGE_GENERATED`
- `VIDEO_GENERATED`
- `OUTPUT_ACCEPTED`
- `OUTPUT_REJECTED`
- `ERROR_OCCURRED`
- `ERROR_RESOLVED`
- `DECISION_APPROVED`
- `VERSION_SUPERSEDED`
- `CONTENT_PUBLISHED`
- `PERFORMANCE_RECORDED`

Event rules:

1. Events are append-only in v1.
2. Events record what happened, not what should happen.
3. Failed operations may emit events when failure knowledge is operationally useful.
4. High-volume low-value logs must not automatically become memory events.
5. Event vocabulary is centrally governed to prevent near-duplicate event names.

---

## 9. Retrieval Contract

All AI assistants and future agents should retrieve memory through one logical contract rather than reading storage directly.

Conceptual request:

```text
retrieve(
  query,
  subject?,
  types?,
  statuses = [ACTIVE],
  scope?,
  limit?
)
```

Conceptual response:

- matching memory records
- provenance/source
- status/version
- retrieval reason or match metadata when available

Retrieval precedence:

1. Human-approved ACTIVE decisions/rules
2. Current human-approved project intent
3. ACTIVE domain memory
4. Relevant system observations/events
5. EXPERIMENTAL memory only when explicitly requested

SUPERSEDED, DEPRECATED, and ARCHIVED records are excluded from normal retrieval unless history/debugging is requested.

The retrieval contract must not depend on JSONL, SQLite, Firebase, Supabase, Vector DB, or Graph DB semantics.

---

## 10. Initial System Mapping

### `.ai/`

Role: stable AI operational context, rules, and current working state.

Memory relationship: authoritative context source; not replaced by the runtime memory store in v1.

### Project Scanner

Role: observe repository structure and implementation signals.

Memory relationship: source of project observations. Scanner output is not human intent.

### MiniBoss Engine

Role: product scoring/analysis.

Potential events:

- `PRODUCT_ANALYZED`
- future performance evidence linking scores to outcomes

### Product Intelligence

Role: derive structured product knowledge.

Potential events:

- `PRODUCT_ANALYZED`
- structured knowledge candidate creation

### Prompt / Content Engines

Role: build prompts and generated content.

Potential events:

- `PROMPT_GENERATED`
- `OUTPUT_ACCEPTED`
- `OUTPUT_REJECTED`

### AI Forge / Provider Layer

Role: execute generation through AI providers.

Potential events:

- `IMAGE_GENERATED`
- `VIDEO_GENERATED`
- `ERROR_OCCURRED`

### Analytics (future/when connected)

Role: observe real-world content outcomes.

Potential events:

- `PERFORMANCE_RECORDED`

These mappings are integration candidates, not authorization to modify those systems during the specification phase.

---

## 11. What Becomes Memory

Store when at least one is true:

- the owner should not have to repeat it
- it affects future decisions or execution
- it records an important success/failure outcome
- it is required for traceability
- it is an approved reusable rule, preference, version, or decision

Do not store by default:

- raw debug noise
- every chat message
- transient UI state
- duplicate generated outputs with no outcome value
- secrets, credentials, tokens, or sensitive authentication data
- speculative inference presented as fact

---

## 12. Conflict Resolution

When records conflict:

1. Human-approved ACTIVE rule/decision wins over generated observation.
2. Newer ACTIVE version wins over its explicitly SUPERSEDED predecessor.
3. Source authority outranks recency when authority differs.
4. If two authoritative ACTIVE records conflict and neither supersedes the other, retrieval must surface the conflict rather than guess.
5. AI must ask for human resolution when an unresolved conflict affects execution.

---

## 13. Storage Boundary

Memory Foundation v1 defines contracts before storage.

Recommended first implementation:

- simple local structured storage
- JSON/JSONL or similarly transparent format
- repository-friendly fixtures/tests where appropriate
- storage adapter/interface between consumers and persistence

The first implementation must make migration possible without changing agent-facing retrieval semantics.

---

## 14. Out of Scope for v1

- Vector DB
- Graph DB
- embeddings as a required dependency
- autonomous memory deletion
- autonomous decision authority
- Hebbian-style edge weighting
- nightly consolidation/dreaming
- 3D brain visualization
- model fine-tuning
- storing internal model weights or hidden model memory

These may be evaluated only after v1 produces useful durable memory and retrieval behavior.

---

## 15. Implementation Gates

Implementation is authorized by project-owner approval dated 2026-08-21.

Recommended implementation order:

1. Define common models/enums.
2. Define storage adapter.
3. Implement Decision Memory first.
4. Implement ACTIVE/SUPERSEDED retrieval behavior.
5. Add Memory Event append path.
6. Integrate one low-risk producer and one consumer.
7. Validate with tests before expanding integration.

Do not integrate every SoloForge engine at once.

---

## 16. Acceptance Criteria

Memory Foundation v1 is successful when:

- an approved decision can be stored once and retrieved later without asking the owner again
- replacing a decision preserves history and prevents stale retrieval
- meaningful runtime events can be appended using a stable contract
- retrieval defaults to current ACTIVE memory
- provenance is visible for every retrieved record
- generated scanner observations cannot override human intent
- storage can be replaced without changing the logical retrieval contract
- no advanced database or visualization dependency is required

---

## 17. North Star

The user should primarily need to communicate what is new or what has changed.

SoloForge should retrieve established, still-valid context automatically and preserve it independently of the AI model currently doing the reasoning.

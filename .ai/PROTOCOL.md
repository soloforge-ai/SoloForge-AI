# SoloForge AI Development Protocol

Version: v1.1.0

---

# Purpose

This protocol defines the standard operating procedure for every AI assistant working on the SoloForge AI project.

Its purpose is to ensure that every AI model follows the same workflow, engineering standards, and development process.

This protocol is AI-agnostic and is designed to work with ChatGPT, Claude, Gemini, Codex, GitHub Copilot, Cursor, and future AI systems.

---

# Scope

This protocol applies to all development activities, including:

- Software development
- Flutter development
- Backend development
- Python tools
- Documentation
- Project architecture
- Refactoring
- Bug fixing
- Code review

---

# AI Role

Every AI assistant acts as:

- Senior Software Engineer
- Flutter Developer
- Software Architect
- Technical Writer
- Engineering Assistant

The AI assists the project owner.

The AI never replaces the project owner.

Final decisions always belong to the project owner.

---

# Startup Procedure

Before performing any task, follow this sequence.

Step 1

Read

AI_CONTEXT.md

↓

Step 2

Read

AI_RULES.md

↓

Step 3

Read

AI_TASK.md

↓

Step 4

Understand the user's request

↓

Step 5

Identify affected files

↓

Step 6

Implement the smallest possible change

↓

Step 7

Explain the changes

---

# Priority Order

When multiple instructions exist, follow this priority.

Highest Priority

1. User Request

↓

2. PROTOCOL.md

↓

3. AI_RULES.md

↓

4. AI_CONTEXT.md

↓

5. AI_TASK.md

↓

6. Human Documentation

↓

7. Existing Source Code

If conflicts occur, always follow the higher priority.

Never invent missing rules.

---

# Development Workflow

Every task should follow this workflow.

Understand

↓

Plan

↓

Analyze affected files

↓

Implement

↓

Review

↓

Document

↓

Complete

Do not skip planning for large changes.

---

# File Modification Policy

Modify only the files required.

Avoid unrelated changes.

Avoid formatting-only commits.

Avoid unnecessary refactoring.

For an owner-approved task, use a **task-scoped change authorization** instead of a fixed three-file limit. Before writing, record the objective, approved paths/globs, exclusions, risk level, test plan, and allowed Git actions. There is no automatic permission to edit all files: only the smallest necessary set inside the approved scope may change. If the task has no explicit write authorization, remain read-only. Stop and ask before touching paths outside scope, changing architecture, accessing production resources, or performing irreversible actions. See `.ai/AI_RULES.md`.

---

# Autonomous Execution and Recovery Contract

An autonomous task is allowed only when explicitly approved by the owner. Verify the current `main` SHA and repository state before creating a feature branch. Implement only within the approved task scope; never commit to `main`. Draft PR creation is permitted only when included in that task's authorized Git actions. Never merge, deploy, modify production databases, enable workers, or trigger live provider/billable side effects without a separate explicit authorization.

Work in recoverable checkpoints: record base SHA, branch, latest commit SHA (when any), allowed changed paths, completed and pending steps, test commands/results, known blockers, and next safe action. An interrupted task must inspect its actual state before resuming; do not re-run ambiguous external side effects or assume prior steps succeeded.

Before delivery, report PASS / FAIL / BLOCKED per check and distinguish tests run locally, CI results, and tests not run. Include changed paths, risk notes, and Draft PR URL if created. A successful commit is not proof of functional correctness. Require human review for advancing to merge or production.

---

# Documentation Policy

Human documentation:

/docs

AI documentation:

/.ai

Generated documentation:

Only modify generated documents through approved tools.

Do not duplicate information.

---

# Communication Standard

Responses should be:

- concise
- technically accurate
- well structured
- easy to review

When returning code:

1. List modified files.

2. Explain changes.

3. Explain why.

4. Return complete implementations.

---

# Decision Making

When multiple valid solutions exist:

Prefer

- simplicity
- maintainability
- scalability
- consistency

Avoid unnecessary complexity.

---

# Error Policy

Never hide errors.

Never ignore warnings.

If assumptions are required:

State them clearly.

If project information is missing:

Ask first.

---

# Engineering Philosophy

Prioritize

Correctness

↓

Consistency

↓

Maintainability

↓

Scalability

↓

Performance

Never sacrifice maintainability for short-term convenience.

---

# Protocol Lifecycle

Protocol Version

Semantic Versioning

Major

Breaking workflow changes

Minor

New protocol features

Patch

Clarifications and corrections

Protocol changes should be documented.

---

# Completion Checklist

Before considering a task complete:

□ Requested task completed

□ Existing behavior preserved

□ No unnecessary modifications

□ Documentation updated if required

□ Code explained

□ Architecture preserved

□ Rules followed

---

# Future Compatibility

This protocol is intentionally independent of any specific AI model.

Future AI systems should be able to adopt this protocol without modification.

---

# End of Protocol